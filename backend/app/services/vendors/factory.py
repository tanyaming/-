from app.models.entities import VendorAccount, VendorType
from app.services.vendors.base import VendorAdapter
from app.services.vendors.jiushi import JiushiAdapter
from app.services.vendors.neolix import NeolixAdapter


def build_vendor_adapter(account: VendorAccount) -> VendorAdapter:
    if account.vendor_type == VendorType.NEOLIX:
        return NeolixAdapter(account)
    if account.vendor_type == VendorType.JIUSHI:
        return JiushiAdapter(account)
    raise ValueError(f"unsupported vendor type: {account.vendor_type}")

