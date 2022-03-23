import re
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.db.models.aggregates import Sum
from django.utils.timezone import localtime, now, datetime
from django.utils import timezone
from django.urls import reverse
from ckeditor.fields import RichTextField

NEWS_TYPE = (
    ('News','News'),
    ('Mom & Baby','Mom & Baby'),
    ('Beauty','Beauty'),
    ('Family & Gender','Family & Gender'),
    ('Nutrition','Nutrition'),
    ('Covid-19','Covid-19'),
    ('Common Diseases','Common Diseases'),
    ('Chronic Diseases','Chronic Diseases')
)

class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError(_('Users must have an email address'))

        user = self.model(
            email=self.normalize_email(email),
        )
        
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_staffuser(self, email, password):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_staff = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_staff = True
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=12, null=True, blank=True)
    address = models.CharField(max_length=255,null=True, blank=True)
    avatar_url = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    zip_code = models.CharField(max_length=100, null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=localtime)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] # Email & Password are required by default.

    objects = UserManager()

    class Meta:
        db_table = "user"
        ordering = ["-created_at"]

    def __str__(self):
        """String for representing the User Model object."""
        return f'{self.last_name} {self.first_name}' if self.last_name and self.first_name else self.username

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_name = models.CharField(max_length=200)
    image = models.ImageField(default='/product_pics/default.png', upload_to='product_pics')
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True)
    brand = models.ForeignKey('Brand', on_delete=models.SET_NULL, null=True)
    age =  models.ForeignKey('Age', on_delete=models.SET_NULL, null=True)
    gender = models.ForeignKey('Gender', on_delete=models.SET_NULL, null=True)
    form = models.ForeignKey('Form', on_delete=models.SET_NULL, null=True)
    tag = models.ManyToManyField('Tag', blank=True, null=True)
    description = RichTextField(help_text=_('Enter a brief description of the product'))
    price = models.FloatField(blank=True, null=True)
    quantity = models.IntegerField(null=True, default=1)
    discount = models.IntegerField(null=True, blank=True)
    discount_expired = models.DateTimeField(default=now, blank=True)
    last_seen = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "product"
        ordering = ["-created_at"]

    def __str__(self):
        """String for representing the Model object."""
        return self.product_name
        
    class Meta:
        verbose_name_plural = "products"

    def get_absolute_url(self):
        return reverse('product-detail', args=[str(self.id)])

    def get_discount_price(self):
        return self.price - (self.discount*self.price)/100 if self.discount!=None and self.discount > 0 else None
    
    def valid_day(self):
        return True if datetime.now(timezone.utc) < self.discount_expired else False 

    def get_total_sales(self):
        return Booking.objects.filter(product=self.id).aggregate(Sum('quantity')).get('quantity__sum', 0)

class Age(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, help_text=_('Enter age'))
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "age"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

class Gender(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, help_text=_('Enter gender name'))
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "gender"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

class Form(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text=_('Enter product form'))
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "form"
        constraints = [
            models.UniqueConstraint(
                fields=["name"], name="unique_form_name"
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

class Navbar(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text=_('Enter navbar name'))
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "navbar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text=_('Enter product subcategory'))
    image = models.ImageField(default='/category_pics/default.png', upload_to='category_pics')
    advert_image = models.ImageField(default='/category_adverts/default.png', upload_to='category_adverts')
    navbar = models.ForeignKey('Navbar', on_delete=models.SET_NULL, null=True)
    is_popular = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "category"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

class Brand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text=_('Enter product brand'))
    image = models.ImageField(default='/brand_pics/default.png', upload_to='brand_pics')
    advert_image = models.ImageField(default='/brand_adverts/default.jpg', upload_to='brand_adverts')
    website = models.CharField(max_length=255, blank=True)
    is_featured = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "brand"
        constraints = [
            models.UniqueConstraint(
                fields=["name"], name="unique_brand_name"
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    total_price = models.FloatField(blank=True, null= True, default=0)
    shipping_address = models.CharField(max_length=200, null= True, help_text=_('Enter your shipping address (e.g. Danang, VietNam)'))
    phone_number = models.CharField(max_length=20, null= True, help_text=_('Enter your phone number (e.g. 840247xxx )'))
    BOOKING_STATUS = (
        ('W','waiting'),
        ('A','approved'),
        ('R','rejected')
    )
    status = models.CharField(choices=BOOKING_STATUS, max_length=2, blank=True, default=BOOKING_STATUS[0][0])
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "order"
        ordering = ["-created_at"]
        permissions = (("can_mark_returned", "Set order as returned"),)
        verbose_name_plural = "orders"

    def __str__(self):
        return f'{self.id} ({self.user.username})'

class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, null=True)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "booking"
        ordering = ["-created_at"]

    def __str__(self):
        return f'{self.quantity}'

class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    title = models.CharField(max_length=500)
    content = models.TextField(max_length=1000)
    rate = models.IntegerField(default=5, validators=[MaxValueValidator(5), MinValueValidator(1)], blank=True, null=True)
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "review"
        ordering = ["-created_at"]

    def __str__(self):
        return f'{self.user.username}, {self.product.product_name}, {self.rate}, {self.created_at}'

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quantity = models.IntegerField(db_column='quantity')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, null=True)

    def get_total_price(self):
        if datetime.now(timezone.utc) < self.product.discount_expired:
            return self.quantity*(self.product.price - (self.product.discount*self.product.price)/100)
        else:
            return self.quantity*self.product.price       

class Coupon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, null=True)
    content = models.CharField(max_length=100, null=True)
    code = models.CharField(max_length=50, null=True)
    value = models.IntegerField(null=True, blank=True)
    coupon_expired = models.DateTimeField(default=now, blank=True, null=True)
    minimum_order = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "coupon"
        ordering = ["-created_at"]

class UseCoupon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True) 
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, null=True)
    saved = models.BooleanField(default=False)
    used = models.BooleanField(default=False)
    applied = models.BooleanField(default=False)

class Favorite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, null=True)
    review = models.ForeignKey('Review', on_delete=models.CASCADE, null=True)
    
    def __str__(self):
        return self.user.username

class News(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, null=True)
    content = RichTextField(help_text=_('Enter a content of the new'))
    image = models.ImageField(default='/news_pics/default.jpg', upload_to='news_pics')
    NEWS_TYPE = (
        ('News','News'),
        ('Mom & Baby','Mom & Baby'),
        ('Beauty','Beauty'),
        ('Family & Gender','Family & Gender'),
        ('Nutrition','Nutrition'),
        ('Covid-19','Covid-19'),
        ('Common Diseases','Common Diseases'),
        ('Chronic Diseases','Chronic Diseases')
    )
    type = models.CharField(choices=NEWS_TYPE, max_length=20)
    viewed = models.IntegerField(null=True, default=0)
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "new"
        ordering = ["-created_at"]

    def __str__(self):
        return f'{self.id} ({self.user.username})'

class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, null=True)
    content = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "report"
        ordering = ["-created_at"]

    def __str__(self):
        return f'{self.user.username} ({self.review.id})'

class Request(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, null=True)
    content = RichTextField(help_text=_('Enter a brief content of the request'), null=True)
    REQUEST_STATUS = (
        ('Sent','Sent'),
        ('Checked','Checked'),
        ('Answered','Answered')
    )
    status = models.CharField(choices=REQUEST_STATUS, max_length=10, blank=True, default=REQUEST_STATUS[0][0])
    answer = RichTextField(help_text=_('Enter a answer for this request'), null=True, blank=True)
    created_at = models.DateTimeField(default=localtime)

    class Meta:
        db_table = "request"
        ordering = ["-created_at"]

    def __str__(self):
        return f'{self.id} ({self.user.username})'

class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tag"
        constraints = [
            models.UniqueConstraint(
                fields=["name"], name="unique_tag_name"
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f'{self.name}'
