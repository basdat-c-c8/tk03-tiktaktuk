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
    DISCOUNT_TYPE_NOMINAL = 'nominal'
    DISCOUNT_TYPE_PERCENTAGE = 'percentage'
    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_TYPE_NOMINAL, 'Nominal'),
        (DISCOUNT_TYPE_PERCENTAGE, 'Persentase'),
    ]

    promotion_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promo_code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default=DISCOUNT_TYPE_NOMINAL)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    quota = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.promo_code

    def is_currently_active(self, today=None):
        from django.utils import timezone

        today = today or timezone.localdate()
        if not self.is_active:
            return False
        if self.start_date and self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True

    def calculate_discount(self, line_total):
        if self.discount_type == self.DISCOUNT_TYPE_PERCENTAGE:
            percentage_discount = (line_total * self.discount_amount) / 100
            return min(percentage_discount, line_total)
        return min(self.discount_amount, line_total)


class OrderPromotion(models.Model):
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE)
    promotion = models.ForeignKey('orders.Promotion', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('order', 'promotion')

    def __str__(self):
        return f"{self.order.order_id} - {self.promotion.promo_code}"
from django.db import models

# Create your models here.
