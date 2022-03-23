from attr import attr, attrs
from django import forms
# from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.forms import models
from django.utils.translation import ugettext_lazy as _
from ckeditor.widgets import CKEditorWidget
from .models import Brand, Cart, Category, Coupon, Navbar, Product, User, Review, Request, News, Age, Form, Gender, Tag, NEWS_TYPE
from .utils.constant import PHONE_NUMBER_VALIDATOR as regex

class UserRegisterForm(UserCreationForm):
    phone_regex = RegexValidator(regex, message=_("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."))
    phone_number = forms.CharField(required=False, validators=[phone_regex], max_length=17, label=_("Phone number"))
    address = forms.CharField(required=False, max_length=255, label=_("Address"))

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2', 'username', 'first_name', 'last_name', 'phone_number', 'address']


class CartForm(forms.ModelForm):
    class Meta:
        model = Cart
        fields = ["quantity"]
        widgets = { 
            'quantity' : forms.NumberInput(attrs={'class':'form-control','min':'1'})
        }

class ReviewForm(forms.ModelForm):
    def clean_rate(self):
        data = self.cleaned_data.get("rate", 5)
        if data < 1 or data > 5:
            raise forms.ValidationError("Rate must be within range 1 to 5")
        if not str(data).isdigit() :
            raise forms.ValidationError("Rate must be interger")
        return data

    class Meta:
        model = Review
        fields = ["rate", "title","content"]
        help_texts = {
            'title': 'Your review title must be at least 10 characters.',
            'content': 'Your review content must be at least 20 characters.'
        }
        widgets = {
            'rate': forms.NumberInput(attrs={'class':'form-control','min':'1','max':'5'}),
            'title': forms.TextInput(attrs={'class':'form-control'}),
            'content': forms.Textarea(attrs={'class':'form-control',"rows": "4","cols": "15"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rate'].widget.attrs.update(size='60')
        self.fields['title'].widget.attrs.update(size='60')
        self.fields['content'].widget.attrs.update(size='60')
        self.fields['title'].help_text = '<small class="form-text text-muted">Your review title must be at least 10 characters.</small>'
        self.fields['content'].help_text = '<small class="form-text text-muted">Your review content must be at least 20 characters.</small>'

class CouponForm(models.ModelForm):
    class Meta:
        model = Coupon
        fields = ["code"]
        widgets = {
            'code' : forms.TextInput(attrs={'class':'form-control','placeholder': 'Enter Coupon Code'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].label = ''

class RequestForm(models.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())
    
    class Meta:
        model = Request
        fields = ["title","content"]
        widgets = {
            'title' : forms.TextInput(attrs={'class':'form-control'})
        }

class AnswerForm(models.ModelForm):
    answer = forms.CharField(widget=CKEditorWidget())
    
    class Meta:
        model = Request
        fields = ["answer",]
        widgets = {
            'answer' : forms.TextInput(attrs={'class':'form-control'})
        }

class NewsForm(models.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())
    
    class Meta:
        model = News
        fields = ["content",]
        widgets = {
            'content' : forms.TextInput(attrs={'class':'form-control'})
        }

class ProductForm(models.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())
    
    class Meta:
        model = Product
        fields = ["description",]
        widgets = {
            'description' : forms.TextInput(attrs={'class':'form-control', "required":"true"})
        }

class AdminProductForm(models.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())
    image=forms.ImageField(widget=forms.FileInput()),

    class Meta:
        model = Product
        category=forms.ModelChoiceField(queryset = Category.objects.all()),
        brand=forms.ModelChoiceField(queryset=Brand.objects.all()),
        age=forms.ModelChoiceField(queryset=Age.objects.all()),
        gender=forms.ModelChoiceField(queryset=Gender.objects.all()),
        form=forms.ModelChoiceField(queryset=Form.objects.all()),
        tag=forms.ModelMultipleChoiceField(queryset=Tag.objects.all()),
        discount_expired=forms.DateTimeField(widget=forms.SplitDateTimeField)
        
        fields = ['product_name','image', 'category', 'brand', 'age', 'gender', 'form', 'tag', 'description','price','quantity','discount','discount_expired']
        
        widgets = {
            'product_name': forms.TextInput(attrs={'class':'form-control','min':'1','max':'5'}),
            'price':forms.NumberInput(attrs={'class':'form-control','min':'0','step': 0.1}),
            'quantity':forms.NumberInput(attrs={'class':'form-control','min':'0'}),
            'discount':forms.NumberInput(attrs={'class':'form-control','min':'0','max':'100'}),
        }

class AdminNavbarForm(models.ModelForm):
    class Meta:
        model = Navbar
        fields = ["name",]
        widgets = {
            'name' : forms.TextInput(attrs={'class':'form-control'})
        }

class AdminCategoryForm(models.ModelForm):
    image=forms.ImageField(widget=forms.FileInput()),
    advert_image=forms.ImageField(widget=forms.FileInput()),

    class Meta:
        model = Category
        navbar=forms.ModelChoiceField(queryset = Navbar.objects.all()),
        is_popular=forms.BooleanField()

        fields = ["name","image","advert_image","navbar","is_popular"]

        widgets = {
            'name' : forms.TextInput(attrs={'class':'form-control'})
        }

class AdminBrandForm(models.ModelForm):
    image=forms.ImageField(widget=forms.FileInput()),
    advert_image=forms.ImageField(widget=forms.FileInput()),

    class Meta:
        model = Brand
        is_featured=forms.BooleanField()

        fields = ["name","image","advert_image","website","is_featured"]

        widgets = {
            'name' : forms.TextInput(attrs={'class':'form-control'}),
            'website' : forms.TextInput(attrs={'class':'form-control'})
        }

class AdminFormForm(models.ModelForm):
    class Meta:
        model = Form
        fields = ["name",]
        widgets = {
            'name' : forms.TextInput(attrs={'class':'form-control'})
        }

class AdminAgeForm(models.ModelForm):
    class Meta:
        model = Age
        fields = ["name",]
        widgets = {
            'name' : forms.TextInput(attrs={'class':'form-control'})
        }

class AdminGenderForm(models.ModelForm):
    class Meta:
        model = Gender
        fields = ["name",]
        widgets = {
            'name' : forms.TextInput(attrs={'class':'form-control'})
        }

class AdminCouponForm(models.ModelForm):
    class Meta:
        model = Coupon
        coupon_expired = forms.DateTimeField(widget=forms.SplitDateTimeField)
        
        fields = ['title','content', 'code', 'value', 'coupon_expired', 'minimum_order']
        
        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control'}),
            'content': forms.TextInput(attrs={'class':'form-control'}),
            'code': forms.TextInput(attrs={'class':'form-control'}),
            'value':forms.NumberInput(attrs={'class':'form-control','min':'0','max':'100'}),
            'minimum_order':forms.NumberInput(attrs={'class':'form-control','min':'0'}),
        }

class AdminTagForm(models.ModelForm):
    class Meta:
        model = Tag
        fields = ["name",]
        widgets = {
            'name' : forms.TextInput(attrs={'class':'form-control'})
        }

class AdminNewsForm(models.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())
    image=forms.ImageField(widget=forms.FileInput()),
    type=forms.CharField(max_length=20, widget=forms.Select(choices=NEWS_TYPE))

    class Meta:
        model = News
        user=forms.ModelChoiceField(queryset = User.objects.filter(is_admin=True)),
        
        fields = ['user','title', 'content', 'image', 'type']
        
        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control'})
        }
