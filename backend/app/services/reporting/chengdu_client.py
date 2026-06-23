import socket
import ssl
from dataclasses import dataclass
from pathlib import Path

from app.services.normalizers.models import StandardVehicleState
from app.services.protocols.chengdu_encoder import (
    ChengduStaticParams,
    encode_fault_state,
    encode_runtime_state,
    encode_static_params,
)


@dataclass
class ChengduConnectionConfig:
    host: str
    port: int
    vehicle_no: str
    cert_file: Path
    key_file: Path | None = None
    ca_file: Path | None = None
    timeout: float = 10.0


class ChengduReportingClient:
    def __init__(self, config: ChengduConnectionConfig) -> None:
        self.config = config
        self._socket: ssl.SSLSocket | None = None
        self._message_no = 0

    def connect(self) -> None:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(self.config.ca_file) if self.config.ca_file else None)
        context.load_cert_chain(certfile=str(self.config.cert_file), keyfile=str(self.config.key_file) if self.config.key_file else None)
        raw = socket.create_connection((self.config.host, self.config.port), timeout=self.config.timeout)
        self._socket = context.wrap_socket(raw, server_hostname=self.config.host)

    def close(self) -> None:
        if self._socket:
            self._socket.close()
            self._socket = None

    def _send(self, payload: bytes) -> None:
        if self._socket is None:
            self.connect()
        assert self._socket is not None
        self._socket.sendall(payload)

    def send_static_params(self, coordinate_system: int = 1) -> None:
        payload = encode_static_params(
            ChengduStaticParams(vehicle_no=self.config.vehicle_no, coordinate_system=coordinate_system)
        )
        self._send(payload)

    def send_runtime_state(self, state: StandardVehicleState) -> int:
        self._message_no = self._message_no + 1 if self._message_no < 9_223_372_036_854_775_806 else 1
        payload = encode_runtime_state(self.config.vehicle_no, self._message_no, state)
        self._send(payload)
        return self._message_no

    def send_fault_state(self, state: StandardVehicleState) -> int:
        self._message_no = self._message_no + 1 if self._message_no < 9_223_372_036_854_775_806 else 1
        payload = encode_fault_state(self.config.vehicle_no, self._message_no, state)
        self._send(payload)
        return self._message_no

