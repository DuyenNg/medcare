from django import forms
# from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db.models import fields
from django.forms import models, widgets
from django.utils.translation import ugettext_lazy as _
from ckeditor.widgets import CKEditorWidget
from .models import Cart, Coupon, User, Review, Request
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
