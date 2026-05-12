from django.db import models


class ShopifyToken(models.Model):
    shop = models.CharField(max_length=255, unique=True)
    access_token = models.TextField()
    scopes = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.shop
