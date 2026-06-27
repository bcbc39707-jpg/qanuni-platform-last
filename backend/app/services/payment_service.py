import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from app.models.payment import PaymentProvider

logger = logging.getLogger(__name__)

@dataclass
class PaymentResult:
    success: bool
    txn_id: Optional[str] = None
    redirect_url: Optional[str] = None
    error: Optional[str] = None

@dataclass
class PaymentRequest:
    amount: float
    currency: str = "YER"
    description: str = ""
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None

class BasePaymentProvider(ABC):
    @abstractmethod
    async def create_payment(self, request: PaymentRequest) -> PaymentResult:
        pass

    @abstractmethod
    async def verify_payment(self, txn_id: str) -> PaymentResult:
        pass

class ManualProvider(BasePaymentProvider):
    async def create_payment(self, request: PaymentRequest) -> PaymentResult:
        return PaymentResult(success=True, txn_id=f"manual_{id(request)}")

    async def verify_payment(self, txn_id: str) -> PaymentResult:
        return PaymentResult(success=True, txn_id=txn_id)

class PaymentService:
    def __init__(self):
        self._providers: dict[PaymentProvider, BasePaymentProvider] = {}

    def register_provider(self, provider: PaymentProvider, impl: BasePaymentProvider):
        self._providers[provider] = impl

    def get_provider(self, provider: PaymentProvider) -> BasePaymentProvider:
        impl = self._providers.get(provider)
        if not impl:
            logger.warning(f"Payment provider {provider.value} not configured, using manual")
            return ManualProvider()
        return impl

    async def create_payment(self, provider: PaymentProvider, request: PaymentRequest) -> PaymentResult:
        impl = self.get_provider(provider)
        result = await impl.create_payment(request)
        logger.info(f"Payment created via {provider.value}: txn={result.txn_id}, success={result.success}")
        return result

    async def verify_payment(self, provider: PaymentProvider, txn_id: str) -> PaymentResult:
        impl = self.get_provider(provider)
        return await impl.verify_payment(txn_id)

payment_service = PaymentService()
