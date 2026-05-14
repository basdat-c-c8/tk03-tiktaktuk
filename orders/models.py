import uuid
from django.db import models


class Order(models.Model):
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE)
    event = models.ForeignKey('accounts.Event', on_delete=models.CASCADE)
    order_datetime = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    payment_status = models.CharField(max_length=30, default='pending')
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"Order {self.order_id} - {self.customer.full_name}"


class Promotion(models.Model):
    promotion_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promo_code = models.CharField(max_length=50, unique=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quota = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.promo_code


class OrderPromotion(models.Model):
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE)
    promotion = models.ForeignKey('orders.Promotion', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('order', 'promotion')

    def __str__(self):
        return f"{self.order.order_id} - {self.promotion.promo_code}"
from django.db import models

# Create your models here.
