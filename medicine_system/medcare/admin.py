from django.contrib import admin
from django import forms
from ckeditor.widgets import CKEditorWidget
from medcare.models import (
    Age, 
    Brand, 
    Category, 
    Form, 
    Gender, 
    Order, 
    Product, 
    Review, 
    User, 
    Cart, 
    Coupon, 
    Navbar, 
    News, 
    Report, 
    Request,
    Tag,
)

@admin.register(User)
class User(admin.ModelAdmin):
    list_display = ('email', 'last_name', 'first_name', 'is_admin', 'is_staff', 'is_active')
    search_fields = ('email', 'last_name', 'first_name')
    ordering = ('email',)

class ProductAdminForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())

class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('id','product_name','image','display_category', 'display_brand','age','gender','form','price','quantity', 'discount','last_seen','created_at')
    list_filter = ('created_at','gender','form','brand')

    def display_category(self, obj):
        return obj.category.name

    def display_brand(self, obj):
        return obj.brand.name
    
    display_category.short_description = 'Category'
    display_brand.short_description = 'Brand'

class BrandAdmin(admin.ModelAdmin):
    list_display = ('id','name','image','advert_image','website','is_featured')

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id','name','image','advert_image','display_navbar','is_popular')

    def display_navbar(self, obj):
        return obj.navbar.name
    
    display_navbar.short_description = 'Navbar'

class NavbarAdmin(admin.ModelAdmin):
    list_display = ('id','name')

class OrderAdmin(admin.ModelAdmin):
    list_display = ('display_user','total_price','status','created_at')
    list_filter = ('created_at','status')
    
    def display_user(self, obj):
        return obj.user.username
    
    display_user.short_description = 'User'

class CartAdmin(admin.ModelAdmin):
    list_display = ('display_product','quantity')

    def display_product(self, obj):
        return obj.product.product_name
    
    display_product.short_description = 'Product name'

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('display_user','display_product','title','content','rate','created_at')
    list_filter = ('created_at','rate')

    def display_user(self, obj):
        return obj.user.username

    def display_product(self, obj):
        return obj.product.product_name
    
    display_user.short_description = 'User'
    display_product.short_description = 'Product name'

class CouponAdmin(admin.ModelAdmin):
    list_display = ('code','value','coupon_expired','minimum_order','title','content')
    list_filter = ('value','minimum_order')

class NewsAdmin(admin.ModelAdmin):
    list_display = ('title','image','type','created_at')
    list_filter = ('type','created_at')

class NewsAdminForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())

class ReportAdmin(admin.ModelAdmin):
    list_display = ('title','content', 'display_review', 'created_at')
    list_filter = ('created_at',)

    def display_review(self, obj):
        return f'{obj.review.title} ({obj.review.content})'

class RequestAdmin(admin.ModelAdmin):
    list_display = ('title','created_at')
    list_filter = ('created_at',)

class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Navbar, NavbarAdmin)
admin.site.register(Coupon, CouponAdmin)
admin.site.register(News, NewsAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Request, RequestAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Age)
admin.site.register(Gender)
admin.site.register(Form)
