import json
from multiprocessing import context
import re
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.template.loader import get_template
from django.forms.models import modelform_factory
from django.http.response import HttpResponse, JsonResponse
from django.core.mail import EmailMessage, message
from django.core import serializers
from django.utils.timezone import datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import redirect, render
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.db.models import Count, query
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from medcare.forms import CartForm, UserRegisterForm, ReviewForm, CouponForm, RequestForm

from medcare.models import (
    Booking, 
    Brand, 
    Cart, 
    Category, 
    Order, 
    Product, 
    User, 
    Review, 
    Age, 
    Form, 
    Gender,
    Coupon, 
    UseCoupon, 
    Favorite, 
    Navbar, 
    News, 
    Report, 
    Request,
    Tag,
)
from medcare.utils.constant import PHONE_NUMBER_VALIDATOR     

from faker import Faker

fake = Faker()

def generate_data(request):
    for i in range(0 , 100):
        Product.objects.create(product_name=fake.product_name())
    return JsonResponse({'status' : 200})

def search_product(request):
    query = request.GET.get('query')
    payload = []
    if query:
        fake_product_objs = Product.objects.filter(Q(product_name__icontains=query) | Q(brand__name__icontains=query))
        
        for fake_product_obj in fake_product_objs:
            payload.append(fake_product_obj.product_name[:30] + (fake_product_obj.product_name[30:], ' . . . ')[len(fake_product_obj.product_name) > 30])

    if request.method == 'POST' and request.is_ajax():
        result = request.POST.get('result', None)
        product = Product.objects.filter(product_name__icontains=result).first()
        return JsonResponse({'product_pk':product.pk})

    return JsonResponse({'status' : 200 , 'data' : payload})

def home(request):
    if request.user.is_authenticated:
        favorite_product_ids = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
        cart_count = Cart.objects.filter(user=request.user).count()
        request.session['cart'] = cart_count
    else:
        favorite_product_ids = {}
        request.session['cart'] = {}

    products = Product.objects.all()
    request.session['pro'] = json.dumps(list(products.values_list('product_name', flat=True)))
    navbars = Navbar.objects.all().order_by('created_at')
    categories = Category.objects.all()
    popular_categories = Category.objects.filter(is_popular=True).order_by('created_at')
    brands = Brand.objects.filter(is_featured=True).order_by('created_at')
    health_concern = Category.objects.filter(navbar__name='Health conditions').order_by('created_at')
    list_trending = list(Booking.objects.values_list('product', flat=True).annotate(count=Count('product')).order_by('-count'))
    trending = Product.objects.filter(pk__in=list_trending)[:8]
    recently = Product.objects.filter(last_seen__gte=timezone.localtime()-timedelta(days=1))
    new_products = Product.objects.order_by('-created_at')[:8]
    coupons = Coupon.objects.all()[:2]
    if request.user.is_authenticated:
        saved_coupons = UseCoupon.objects.filter(user=request.user, saved=True).values_list('coupon_id', flat=True)
        used_coupons = UseCoupon.objects.filter(user=request.user, used=True).values_list('coupon_id', flat=True)
    else:
        saved_coupons = None
        used_coupons = None

    coupon_form = CouponForm()

    obj_paginator = Paginator(products, 12)
    first_page = obj_paginator.page(1).object_list
    page_range = obj_paginator.page_range
    
    context = {
        'obj_paginator': obj_paginator,
        'first_page':first_page,
        'page_range':page_range,
        'categories':categories,
        'popular_categories':popular_categories,
        'health_concern':health_concern,
        'navbars':navbars,
        'brands':brands,
        'new_products':new_products,
        'trending':trending,
        'recently':recently,
        'coupons':coupons,
        'saved_coupons':saved_coupons,
        'used_coupons':used_coupons,
        'coupon_form':coupon_form,
        'favorite_product_ids':favorite_product_ids,
        'products':products,
    }

    if request.method == 'POST' and request.is_ajax() and request.POST['action'] == 'saveCoupon':
        coupon_id = request.POST.get('id', None)
        coupon_available = UseCoupon.objects.filter(user=request.user, coupon=coupon_id).first()

        if coupon_available:
            applied_coupon = UseCoupon.objects.get(user=request.user, id=coupon_available.id)
            applied_coupon.saved = True
            applied_coupon.save()
        else:
            applied_coupon = UseCoupon(user=request.user, saved=True, used= False, applied=False, coupon=Coupon.objects.get(id=coupon_id))
            applied_coupon.save()
        
        return JsonResponse({"status":"success", "message":"Coupon code was saved successfully",'coupon_pk':applied_coupon.coupon.pk})

    if request.method == 'POST' and request.is_ajax() and request.POST['action'] == 'pagi':
        page_no = request.POST.get('page_no', None)
        products = obj_paginator.get_page(page_no)
        
        context = {
            "products":products,
            "status":200,
            "favorite_product_ids":favorite_product_ids
        }

        data = {}
        data['list'] = render_to_string('medcare/block/product_block.html',context=context, request=request)
        return JsonResponse(data)
    
    if request.method == 'POST' and request.is_ajax() and request.POST['action'] == 'addWishlist':
        product_id = request.POST.get('id', None)
        in_wishlist = Favorite.objects.filter(user=request.user, product__pk=product_id).first()
        favorite_product_ids = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
        if in_wishlist:
            in_wishlist.delete()
            liked = False
            return JsonResponse({"status":"success","favorite_product_ids":list(favorite_product_ids),"liked":liked, "message":_("You deleted a product from your wishlist")})
        else:
            new_obj = Favorite.objects.create(user=request.user, product_id=product_id)        
            new_obj.save()
            liked = True
            return JsonResponse({"status":"success","favorite_product_ids":list(favorite_product_ids),"liked":liked, "message":_("You added a product to your wishlist")})
    
    if request.method == 'POST' and request.is_ajax() and request.POST['action'] == 'addHelpful':
        review_id = request.POST.get('id', None)
        in_favorite = Favorite.objects.filter(user=request.user, review__pk=review_id).first()
        favorite_review_ids = Favorite.objects.filter(user=request.user).values_list('review_id', flat=True)
        if in_favorite:
            in_favorite.delete()
            liked = False
            return JsonResponse({"status":"success","favorite_review_ids":list(favorite_review_ids),"liked":liked})
        else:
            new_obj = Favorite.objects.create(user=request.user, review_id=review_id)        
            new_obj.save()
            liked = True
            return JsonResponse({"status":"success","favorite_review_ids":list(favorite_review_ids),"liked":liked})
    
    return render(request, 'medcare/home.html',context=context)

def product_detail(request, pk):
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        request.session['cart'] = cart_count
        rv = Review.objects.filter(user=request.user, product__pk=pk).first()
        favorite_review_ids = Favorite.objects.filter(user=request.user).values_list('review_id', flat=True)
    else:
        request.session['cart'] = {}
        rv = None
        favorite_review_ids = {}

    navbars = Navbar.objects.all()
    categories = Category.objects.all()
    product = Product.objects.filter(pk=pk).first()
    product.last_seen = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
    product.save()
    related_products = Product.objects.filter(category = product.category).exclude(id=pk)
    cart_form = CartForm(initial={'quantity': 0})
    pd = Booking.objects.select_related('order').filter(product__pk=pk)
    paid = True if pd else False

    reviewed = True if rv else False
    if(rv):
        review_form = ReviewForm(initial={'rate': rv.rate, 'title': rv.title, 'content': rv.content })
    else:
        review_form = ReviewForm()

    count1 = Review.objects.filter(product__pk=pk).count() - 2
    count2 = Review.objects.filter(product__pk=pk).count()
    five_stars = Review.objects.filter(product__pk=pk, rate=5).count()
    four_stars = Review.objects.filter(product__pk=pk, rate=4).count()
    three_stars = Review.objects.filter(product__pk=pk, rate=3).count()
    two_stars = Review.objects.filter(product__pk=pk, rate=2).count()
    one_star = Review.objects.filter(product__pk=pk, rate=1).count()

    if(count2 == 0):
        average = 5
        five_percentage = 100
        four_percentage = 0
        three_percentage = 0
        two_percentage = 0
        one_percentage = 0
    else:
        average = round(((5*five_stars + 4*four_stars + 3*three_stars + 2*two_stars + 1*one_star) / count2),1)
        five_percentage = int((five_stars/count2)*100)
        four_percentage = int((four_stars/count2)*100)
        three_percentage = int((three_stars/count2)*100)
        two_percentage = int((two_stars/count2)*100)
        one_percentage = int((one_star/count2)*100)
    
    review = Review.objects.filter(product__pk=pk).order_by('created_at')
    review_paginator = Paginator(review, 2)
    first_page = review_paginator.page(1).object_list
    page_range = review_paginator.page_range.stop

    context = {
        'product':product,
        'tags': product.tag.all(),
        'categories':categories,
        'navbars':navbars,
        'related_products':related_products,
        'favorite_review_ids':favorite_review_ids,
        'cart_form':cart_form,
        'paid':paid,
        'review_form':review_form,
        'review':review,
        'first_page':first_page,
        'page_range':page_range,
        'id':pk,
        'count1':count1,
        'count2':count2,
        'reviewed':reviewed,
        'average':average,
        'five_percentage':five_percentage,
        'four_percentage':four_percentage,
        'three_percentage':three_percentage,
        'two_percentage':two_percentage,
        'one_percentage':one_percentage
    }

    if request.method == 'POST' and request.is_ajax():
        page_no = request.POST.get('page_no', None)
        count = request.POST.get('count', None)
        rs = list(review_paginator.page(page_no).object_list.values('id','user__first_name','user__last_name','rate','title','content','created'))
        page_no = int(page_no) + 1
        count = int(count) - 2
        return JsonResponse({"status":200, 'results':rs, 'page_no':str(page_no), 'count':str(count)})

    return render(request,'medcare/product_detail.html',context=context)

def wishlist(request):
    wishlist = Favorite.objects.filter(user=request.user, product_id__isnull=False)
    navbars = Navbar.objects.all()
    categories = Category.objects.all()

    if request.method == 'POST' and request.is_ajax() and request.POST['action'] == 'remove':
        product_id = request.POST.get('id', None)
        in_wishlist = Favorite.objects.filter(user=request.user, product__pk=product_id).first()
        if in_wishlist:
            in_wishlist.delete()
            return JsonResponse({"status":"success", "count":wishlist.count(),"message":_("You deleted a product from your wishlist")})

    if request.method == 'POST' and request.is_ajax() and request.POST.get('action') == 'filter':
        type = request.POST.get('type', None)
        if type == 'rating':
            rate_product = Favorite.objects.filter(user=request.user).order_by('product__review__rate')
            context = {
                "products":rate_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/wishlist_product_block.html',context=context, request=request)
            return JsonResponse(data)
        elif type == 'increase':
            increase_product = Favorite.objects.filter(user=request.user).order_by('product__price')
            context = {
                "products":increase_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/wishlist_product_block.html',context=context, request=request)
            return JsonResponse(data)
        elif type == 'descrease':
            descrease_product = Favorite.objects.filter(user=request.user).order_by('-product__price')
            context = {
                "products":descrease_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/wishlist_product_block.html',context=context, request=request)
            return JsonResponse(data)
        elif type == 'discount':
            discount_product = Favorite.objects.filter(user=request.user).order_by('-product__discount')
            context = {
                "products":discount_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/wishlist_product_block.html',context=context, request=request)
            return JsonResponse(data)

    context = {
        'wishlist':wishlist,
        'categories':categories,
        'navbars':navbars,
        'count':wishlist.count(),
    }

    return render(request, 'medcare/wishlist.html', context=context)

@login_required
def previously_order_product(request):
    product_ids = Booking.objects.filter(order__user=request.user).values_list('product', flat=True).distinct()
    products = Product.objects.all()
    navbars = Navbar.objects.all()
    categories = Category.objects.all()
    if request.user.is_authenticated:
        favorite_product_ids = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    else:
        favorite_product_ids = {}

    context = {
        'product_ids':product_ids,
        'products':products,
        'categories':categories,
        'navbars':navbars,
        'count':product_ids.count(),
        'favorite_product_ids':favorite_product_ids,
    }
    return render(request, 'medcare/previously_order_product.html', context=context)

def product_list(request):
    products = Product.objects.filter(product_name__istartswith="a")
    navbars = Navbar.objects.all()
    categories = Category.objects.all()
    if request.user.is_authenticated:
        favorite_product_ids = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    else:
        favorite_product_ids = {}

    if request.method == 'POST' and request.is_ajax() and request.POST.get('action') == 'filter':
        char = request.POST.get('char', None)
        products = Product.objects.filter(product_name__istartswith=char)
        context = {
            "products":products,
            "favorite_product_ids":favorite_product_ids,
            "status":200
        }
        data = {}
        data['list'] = [render_to_string('medcare/block/product_block.html',context=context, request=request),
        {
            "char":char,
            'count':products.count(),
        }]
        return JsonResponse(data)

    context = {
        'products':products,
        'categories':categories,
        'navbars':navbars,
        'count':products.count(),
    }

    return render(request, 'medcare/product_list.html', context=context)

def news_list(request, type):
    if type == "News":
        news = News.objects.all()
    else:
        news = News.objects.filter(type=type)
    navbars = Navbar.objects.all()
    categories = Category.objects.all()
    most_viewed_news = News.objects.order_by('-viewed')[:5]

    news_paginator = Paginator(news, 12)
    news_page_number =  request.GET.get('page')
    news_page_obj = news_paginator.get_page(news_page_number)

    context = {
        'news_paginator': news_paginator,
        'news_page_obj': news_page_obj,
        'news': news,
        'most_viewed_news':most_viewed_news,
        'categories':categories,
        'navbars':navbars,
        'count':news.count(),
        'type': type,
    }
    return render(request, 'medcare/news_list.html', context=context)

def news_detail(request, pk):
    navbars = Navbar.objects.all()
    categories = Category.objects.all()
    new =  News.objects.filter(id=pk).first()
    most_viewed_news = News.objects.order_by('-viewed')[:5]

    new.viewed+=1
    new.save()

    context = {
        'categories':categories,
        'navbars':navbars,
        'new':new,
        'most_viewed_news':most_viewed_news,
    }
    return render(request, 'medcare/news_detail.html', context=context)

def brand_list(request):
    brands = Brand.objects.all()
    navbars = Navbar.objects.all()
    categories = Category.objects.all()

    if request.method == 'POST' and request.is_ajax() and request.POST.get('action') == 'filter':
        char = request.POST.get('char', None)
        brands = Brand.objects.filter(name__istartswith=char)
        context = {
            "brands":brands,
            "status":200
        }
        data = {}
        data['list'] = [render_to_string('medcare/block/brand_list_block.html',context=context, request=request),
        {
            "char":char,
            'count':brands.count(),
        }]
        return JsonResponse(data)

    context = {
        'brands': brands,
        'categories':categories,
        'navbars':navbars,
        'count':brands.count(),
    }
    return render(request, 'medcare/brand_list.html', context=context)

def brand_get(request, pk):
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        request.session['cart'] = cart_count
    else:
        request.session['cart'] = {}

    brand = Brand.objects.filter(pk=pk).first()
    navbars = Navbar.objects.all()
    categories = Category.objects.all()
    rate_product = Product.objects.filter(brand=pk)
    
    if request.method == 'POST' and request.is_ajax() and request.POST.get('action') == 'Small':
        id = request.POST.get('id', None)
        type = request.POST.get('type', None)
        form = request.POST.get('formOption', None)
        age = request.POST.get('ageOption', None)
        gender = request.POST.get('genderOption', None)
        if type == 'rating':
            if(form == None and age != None and gender != None):
                rate_product = Product.objects.filter(brand=pk, age__name=age, gender__name=gender).order_by('review__rate')
            elif(age == None and form != None and gender != None):
                rate_product = Product.objects.filter(brand=pk, form__name=form, gender__name=gender).order_by('review__rate')
            elif(gender == None and form != None and age != None):
                rate_product = Product.objects.filter(brand=pk, form__name=form, age__name=age).order_by('review__rate')
            elif(age == None and gender == None and form != None):
                rate_product = Product.objects.filter(brand=pk, form__name=form).order_by('review__rate')
            elif(form == None and gender == None and age != None):
                rate_product = Product.objects.filter(brand=pk, age__name=age).order_by('review__rate')
            elif(form == None and age == None and gender != None):
                rate_product = Product.objects.filter(brand=pk, gender__name=gender).order_by('review__rate')
            elif(form != None and age != None, gender !=None):
                rate_product = Product.objects.filter(brand=pk, form__name=form, age__name=age, gender__name=gender).order_by('review__rate')
            
            if(form == None and age == None and gender == None):
                rate_product = Product.objects.filter(brand=pk).order_by('review__rate')

            context = {
                "products":rate_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/brand_product_block.html',context=context, request=request)
            return JsonResponse(data)
        elif type == 'increase':
            if(form == None and age != None and gender != None):
                increase_product = Product.objects.filter(brand=pk, age__name=age, gender__name=gender).order_by('price')
            elif(age == None and form != None and gender != None):
                increase_product = Product.objects.filter(brand=pk, form__name=form, gender__name=gender).order_by('price')
            elif(gender == None and form != None and age != None):
                increase_product = Product.objects.filter(brand=pk, form__name=form, age__name=age).order_by('price')
            elif(age == None and gender == None and form != None):
                increase_product = Product.objects.filter(brand=pk, form__name=form).order_by('price')
            elif(form == None and gender == None and age != None):
                increase_product = Product.objects.filter(brand=pk, age__name=age).order_by('price')
            elif(form == None and age == None and gender != None):
                increase_product = Product.objects.filter(brand=pk, gender__name=gender).order_by('price')
            elif(form != None and age != None, gender !=None):
                increase_product = Product.objects.filter(brand=pk, form__name=form, age__name=age, gender__name=gender).order_by('price')

            if(form == None and age == None and gender == None):
                increase_product = Product.objects.filter(brand=pk).order_by('price')
            context = {
                "products":increase_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/brand_product_block.html',context=context, request=request)
            return JsonResponse(data)
        elif type == 'descrease':
            if(form == None and age != None and gender != None):
                descrease_product = Product.objects.filter(brand=pk, age__name=age, gender__name=gender).order_by('-price')
            elif(age == None and form != None and gender != None):
                descrease_product = Product.objects.filter(brand=pk, form__name=form, gender__name=gender).order_by('-price')
            elif(gender == None and form != None and age != None):
                descrease_product = Product.objects.filter(brand=pk, form__name=form, age__name=age).order_by('-price')
            elif(age == None and gender == None and form != None):
                descrease_product = Product.objects.filter(brand=pk, form__name=form).order_by('-price')
            elif(form == None and gender == None and age != None):
                descrease_product = Product.objects.filter(brand=pk, age__name=age).order_by('-price')
            elif(form == None and age == None and gender != None):
                descrease_product = Product.objects.filter(brand=pk, gender__name=gender).order_by('-price')
            elif(form != None and age != None, gender !=None):
                descrease_product = Product.objects.filter(brand=pk, form__name=form, age__name=age, gender__name=gender).order_by('-price')
            
            if(form == None and age == None and gender == None):
                descrease_product = Product.objects.filter(brand=pk).order_by('-price')

            context = {
                "products":descrease_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/brand_product_block.html',context=context, request=request)
            return JsonResponse(data)
        elif type == 'discount':
            if(form == None and age != None and gender != None):
                discount_product = Product.objects.filter(brand=pk, age__name=age, gender__name=gender).order_by('-discount')
            elif(age == None and form != None and gender != None):
                discount_product = Product.objects.filter(brand=pk, form__name=form, gender__name=gender).order_by('-discount')
            elif(gender == None and form != None and age != None):
                discount_product = Product.objects.filter(brand=pk, form__name=form, age__name=age).order_by('-discount')
            elif(age == None and gender == None and form != None):
                discount_product = Product.objects.filter(brand=pk, form__name=form).order_by('-discount')
            elif(form == None and gender == None and age != None):
                discount_product = Product.objects.filter(brand=pk, age__name=age).order_by('-discount')
            elif(form == None and age == None and gender != None):
                discount_product = Product.objects.filter(brand=pk, gender__name=gender).order_by('-discount')
            elif(form != None and age != None, gender !=None):
                discount_product = Product.objects.filter(brand=pk, form__name=form, age__name=age, gender__name=gender).order_by('-discount')
            
            if(form == None and age == None and gender == None):
                discount_product = Product.objects.filter(brand=pk).order_by('-discount')

            context = {
                "products":discount_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/brand_product_block.html',context=context, request=request)
            return JsonResponse(data)

    # Form filter
    list_form = list(Product.objects.filter(brand=pk).values_list('form', flat=True).distinct())
    form_check = Form.objects.filter(pk__in=list_form).annotate(Count('product'))
    a = Brand.objects.filter(pk=pk).annotate(Count('product')).values_list('product__form__name', 'product__count').order_by('-product__count')
    forms = list(a)

    # Gender filter
    list_gender = list(Product.objects.filter(brand=pk).values_list('gender', flat=True).distinct())
    gender_check = Gender.objects.filter(pk__in=list_gender).annotate(Count('product'))
    b = Brand.objects.filter(pk=pk).annotate(Count('product')).values_list('product__gender__name', 'product__count').order_by('-product__count')
    genders = list(b)

    # Age filter
    list_age = list(Product.objects.filter(brand=pk).values_list('age', flat=True).distinct())
    age_check = Age.objects.filter(pk__in=list_age).annotate(Count('product'))
    c = Brand.objects.filter(pk=pk).annotate(Count('product')).values_list('product__age__name', 'product__count').order_by('-product__count')
    ages = list(c)
    
    # Paginator
    product_list = Product.objects.filter(brand=pk)
    page = request.GET.get('page', 1)
    paginator = Paginator(product_list, 9)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    context = {
        'products':products,
        'categories':categories,
        'navbars':navbars,
        'forms':forms,
        'genders':genders,
        'ages':ages,
        'brand': brand,
        'form_check':form_check,
        'age_check':age_check,
        'gender_check':gender_check
    }

    if request.method == 'POST' and request.is_ajax() and request.POST['action'] == 'Big':
        form = request.POST.get('formOption', '')
        age = request.POST.get('ageOption', '')
        gender = request.POST.get('genderOption', '')
        id = request.POST.get('$id',pk)
        form_disable = False
        age_disable = False
        gender_disable = False
        form_delete = False
        age_delete = False
        gender_delete = False
        type = 0
        # Choose age radio and gender radio
        if form == '' and age != '' and gender != '':
            products = Product.objects.filter(brand=id, age__name=age, gender__name=gender)
            forms = list(Brand.objects.filter(pk=pk, product__age__name=age, product__gender__name=gender).annotate(Count('product')).values_list('product__form__name', 'product__count').order_by('-product__count'))
            type = 1
            if len(forms) == 0 :
                form_delete = True
            if len(forms) == 1 :
                form_disable = True
        # Choose gender radio
        elif form == '' and age == '' and gender != '':
            products = Product.objects.filter(brand=id, gender__name=gender)
            forms = list(Brand.objects.filter(pk=pk, product__gender__name=gender).annotate(Count('product')).values_list('product__form__name', 'product__count').order_by('-product__count'))
            ages = list(Brand.objects.filter(pk=pk, product__gender__name=gender).annotate(Count('product')).values_list('product__age__name', 'product__count').order_by('-product__count'))
            type = 2
            if len(forms) == 0:
                form_delete = True
            if len(ages) == 0:
                age_delete = True
            if len(forms) == 1 :
                form_disable = True
            if len(ages) == 1 :
                age_disable = True
        # Choose form radio and gender radio
        elif age == '' and form != '' and gender != '':
            products = Product.objects.filter(brand=id, form__name=form, gender__name=gender)
            ages = list(Brand.objects.filter(pk=pk, product__form__name = form, product__gender__name = gender).annotate(Count('product')).values_list('product__age__name', 'product__count').order_by('-product__count'))
            type = 3
            if len(ages) == 0:
                age_delete = True
            if len(ages) == 1 :
                age_disable = True
        # Choose form radio
        elif age == '' and gender == '' and form != '':
            products = Product.objects.filter(brand=id, form__name=form)
            ages = list(Brand.objects.filter(pk=pk, product__form__name = form).annotate(Count('product')).values_list('product__age__name', 'product__count').order_by('-product__count'))
            genders = list(Brand.objects.filter(pk=pk, product__form__name = form).annotate(Count('product')).values_list('product__gender__name', 'product__count').order_by('-product__count'))
            type = 4
            if len(ages) == 0:
                age_delete = True
            if len(genders) == 0:
                gender_delete = True
            if len(ages) == 1 :
                age_disable = True
            if len(genders) == 1 :
                gender_disable = True
        # Choose age radio
        elif gender == '' and form == '' and age != '':
            products = Product.objects.filter(brand=id, age__name=age)
            forms = list(Brand.objects.filter(pk=pk, product__age__name = age).annotate(Count('product')).values_list('product__form__name', 'product__count').order_by('-product__count'))
            genders = list(Brand.objects.filter(pk=pk, product__age__name = age).annotate(Count('product')).values_list('product__gender__name', 'product__count').order_by('-product__count'))
            type = 5
            if len(forms) == 0:
                form_delete = True
            if len(genders) == 0:
                gender_delete = True
            if len(forms) == 1 :
                form_disable = True
            if len(genders) == 1 :
                gender_disable = True
        # Choose form radio, age radio
        elif gender == '' and form != '' and age != '':
            products = Product.objects.filter(brand=id, form__name=form, age__name=age)
            genders = list(Brand.objects.filter(pk=pk, product__form__name = form, product__age__name = age).annotate(Count('product')).values_list('product__gender__name', 'product__count').order_by('-product__count'))
            type = 6
            if len(genders) == 0:
                gender_delete = True
            if len(genders) == 1 :
                gender_disable = True
        # Choose form radio, age radio and gender radio
        elif age != '' and form !='' and gender !='':
            products = Product.objects.filter(brand=id, form__name=form, age__name=age, gender__name=gender)
            forms = list(Brand.objects.filter(pk=pk, product__age__name = age, product__form__name = form, product__gender__name = gender).annotate(Count('product')).values_list('product__form__name', 'product__count').order_by('-product__count'))
            ages = list(Brand.objects.filter(pk=pk, product__form__name = form, product__age__name = age, product__gender__name = gender).annotate(Count('product')).values_list('product__age__name', 'product__count').order_by('-product__count'))
            genders = list(Brand.objects.filter(pk=pk, product__form__name = form, product__age__name = age, product__gender__name = gender).annotate(Count('product')).values_list('product__gender__name', 'product__count').order_by('-product__count'))
            type = 7

        context = {
            "products":products,
            "status":200
        }
        data = {}
        data['list'] = [render_to_string('medcare/block/brand_product_block.html',context=context, request=request),
            {
                'type': type,
                'forms':forms, 
                'ages':ages, 
                'genders':genders, 
                'brand_pk':id, 
                'form_delete': form_delete, 
                'age_delete':age_delete, 
                'gender_delete': gender_delete, 
                'gender_disable':gender_disable,
                'form_disable':form_disable,
                'age_disable':age_disable}
        ]
        return JsonResponse(data)
        
    return render(request,'medcare/brand_product.html', context=context)

def category_list(request):
    categories = Category.objects.all()
    navbars = Navbar.objects.all()

    if request.method == 'POST' and request.is_ajax() and request.POST.get('action') == 'filter':
        char = request.POST.get('char', None)
        categories = Category.objects.filter(name__istartswith=char)
        context = {
            "categories":categories,
            "status":200
        }
        data = {}
        data['list'] = [render_to_string('medcare/block/category_list_block.html',context=context, request=request),
        {
            "char":char,
            'count':categories.count(),
        }]
        return JsonResponse(data)

    context = {
        'navbars':navbars,
        'categories': categories,
        'count':categories.count(),
    }
    return render(request, 'medcare/category_list.html', context=context)

def category_get(request, pk):
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        request.session['cart'] = cart_count
    else:
        request.session['cart'] = {}

    categories = Category.objects.all()
    navbars = Navbar.objects.all()
    category = Category.objects.filter(pk=pk).first()
    rate_product = Product.objects.filter(category=pk)
    
    if request.method == 'POST' and request.is_ajax() and request.POST.get('action') == 'Small':
        type = request.POST.get('type', None)
        form = request.POST.get('formOption', None)
        age = request.POST.get('ageOption', None)
        brand = request.POST.get('brandOption', None)
        if type == 'rating':
            if(form == None and age != None and brand != None):
                rate_product = Product.objects.filter(category=pk, age__name=age, brand__name=brand).order_by('review__rate')
            elif(age == None and form != None and brand != None):
                rate_product = Product.objects.filter(category=pk, form__name=form, brand__name=brand).order_by('review__rate')
            elif(brand == None and form != None and age != None):
                rate_product = Product.objects.filter(category=pk, form__name=form, age__name=age).order_by('review__rate')
            elif(age == None and brand == None and form != None):
                rate_product = Product.objects.filter(category=pk, form__name=form).order_by('review__rate')
            elif(form == None and brand == None and age != None):
                rate_product = Product.objects.filter(category=pk, age__name=age).order_by('review__rate')
            elif(form == None and age == None and brand != None):
                rate_product = Product.objects.filter(category=pk, brand__name=brand).order_by('review__rate')
            elif(form != None and age != None, brand !=None):
                rate_product = Product.objects.filter(category=pk, form__name=form, age__name=age, brand__name=brand).order_by('review__rate')
            
            if(form == None and age == None and brand == None):
                rate_product = Product.objects.filter(category=pk).order_by('review__rate')

            context = {
                "products":rate_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/brand_product_block.html',context=context, request=request)
            return JsonResponse(data)
        elif type == 'increase':
            if(form == None and age != None and brand != None):
                increase_product = Product.objects.filter(category=pk, age__name=age, brand__name=brand).order_by('price')
            elif(age == None and form != None and brand != None):
                increase_product = Product.objects.filter(category=pk, form__name=form, brand__name=brand).order_by('price')
            elif(brand == None and form != None and age != None):
                increase_product = Product.objects.filter(category=pk, form__name=form, age__name=age).order_by('price')
            elif(age == None and brand == None and form != None):
                increase_product = Product.objects.filter(category=pk, form__name=form).order_by('price')
            elif(form == None and brand == None and age != None):
                increase_product = Product.objects.filter(category=pk, age__name=age).order_by('price')
            elif(form == None and age == None and brand != None):
                increase_product = Product.objects.filter(category=pk, brand__name=brand).order_by('price')
            elif(form != None and age != None, brand !=None):
                increase_product = Product.objects.filter(category=pk, form__name=form, age__name=age, brand__name=brand).order_by('price')
            
            if(form == None and age == None and brand == None):
                increase_product = Product.objects.filter(category=pk).order_by('price')

            context = {
                "products":increase_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/brand_product_block.html',context=context, request=request)
            return JsonResponse(data)
        elif type == 'descrease':
            if(form == None and age != None and brand != None):
                descrease_product = Product.objects.filter(category=pk, age__name=age, brand__name=brand).order_by('-price')
            elif(age == None and form != None and brand != None):
                descrease_product = Product.objects.filter(category=pk, form__name=form, brand__name=brand).order_by('-price')
            elif(brand == None and form != None and age != None):
                descrease_product = Product.objects.filter(category=pk, form__name=form, age__name=age).order_by('-price')
            elif(age == None and brand == None and form != None):
                descrease_product = Product.objects.filter(category=pk, form__name=form).order_by('-price')
            elif(form == None and brand == None and age != None):
                descrease_product = Product.objects.filter(category=pk, age__name=age).order_by('-price')
            elif(form == None and age == None and brand != None):
                descrease_product = Product.objects.filter(category=pk, brand__name=brand).order_by('-price')
            elif(form != None and age != None, brand !=None):
                descrease_product = Product.objects.filter(category=pk, form__name=form, age__name=age, brand__name=brand).order_by('-price')
            
            if(form == None and age == None and brand == None):
                descrease_product = Product.objects.filter(category=pk).order_by('price')

            context = {
                "products":descrease_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/brand_product_block.html',context=context, request=request)
            return JsonResponse(data)
        elif type == 'discount':
            if(form == None and age != None and brand != None):
                discount_product = Product.objects.filter(category=pk, age__name=age, brand__name=brand).order_by('-discount')
            elif(age == None and form != None and brand != None):
                discount_product = Product.objects.filter(category=pk, form__name=form, brand__name=brand).order_by('-discount')
            elif(brand == None and form != None and age != None):
                discount_product = Product.objects.filter(category=pk, form__name=form, age__name=age).order_by('-discount')
            elif(age == None and brand == None and form != None):
                discount_product = Product.objects.filter(category=pk, form__name=form).order_by('-discount')
            elif(form == None and brand == None and age != None):
                discount_product = Product.objects.filter(category=pk, age__name=age).order_by('-discount')
            elif(form == None and age == None and brand != None):
                discount_product = Product.objects.filter(category=pk, brand__name=brand).order_by('-discount')
            elif(form != None and age != None, brand !=None):
                discount_product = Product.objects.filter(category=pk, form__name=form, age__name=age, brand__name=brand).order_by('-discount')
            
            if(form == None and age == None and brand == None):
                discount_product = Product.objects.filter(category=pk).order_by('-discount')

            context = {
                "products":discount_product,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/brand_product_block.html',context=context, request=request)
            return JsonResponse(data)

    # Form filter
    list_form = list(Product.objects.filter(category=pk).values_list('form', flat=True).distinct())
    form_check = Form.objects.filter(pk__in=list_form).annotate(Count('product'))
    a = Category.objects.filter(pk=pk).annotate(Count('product')).values_list('product__form__name', 'product__count').order_by('-product__count')
    forms = list(a)

    # Brand filter
    list_brand = list(Product.objects.filter(category=pk).values_list('brand', flat=True).distinct())
    brand_check = Brand.objects.filter(pk__in=list_brand).annotate(Count('product'))
    b = Category.objects.filter(pk=pk).annotate(Count('product')).values_list('product__brand__name', 'product__count').order_by('-product__count')
    brands = list(b)

    # Age filter
    list_age = list(Product.objects.filter(category=pk).values_list('age', flat=True).distinct())
    age_check = Age.objects.filter(pk__in=list_age).annotate(Count('product'))
    c = Category.objects.filter(pk=pk).annotate(Count('product')).values_list('product__age__name', 'product__count').order_by('-product__count')
    ages = list(c)
    
    # Paginator
    product_list = Product.objects.filter(category=pk)
    page = request.GET.get('page', 1)
    paginator = Paginator(product_list, 9)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    context = {
        'products':products,
        'navbars':navbars,
        'categories': categories,
        'forms':forms,
        'brands':brands,
        'ages':ages,
        'category': category,
        'form_check':form_check,
        'age_check':age_check,
        'brand_check':brand_check
    }

    if request.method == 'POST' and request.is_ajax() and request.POST['action'] == 'Big':
        form = request.POST.get('formOption', '')
        age = request.POST.get('ageOption', '')
        brand = request.POST.get('brandOption', '')
        id = request.POST.get('$id',pk)
        form_disable = False
        age_disable = False
        brand_disable = False
        form_delete = False
        age_delete = False
        brand_delete = False
        type = 0
        # Choose age radio and brand radio
        if form == '' and age != '' and brand != '':
            products = Product.objects.filter(category=id, age__name=age, brand__name=brand)
            forms = list(Category.objects.filter(pk=pk, product__age__name=age, product__brand__name=brand).annotate(Count('product')).values_list('product__form__name', 'product__count').order_by('-product__count'))
            type = 1
            if len(forms) == 0 :
                form_delete = True
            if len(forms) == 1 :
                form_disable = True
        # Choose brand radio
        elif form == '' and age == '' and brand != '':
            products = Product.objects.filter(category=id, brand__name=brand)
            forms = list(Category.objects.filter(pk=pk, product__brand__name=brand).annotate(Count('product')).values_list('product__form__name', 'product__count').order_by('-product__count'))
            ages = list(Category.objects.filter(pk=pk, product__brand__name=brand).annotate(Count('product')).values_list('product__age__name', 'product__count').order_by('-product__count'))
            type = 2
            if len(forms) == 0:
                form_delete = True
            if len(ages) == 0:
                age_delete = True
            if len(forms) == 1 :
                form_disable = True
            if len(ages) == 1 :
                age_disable = True
        # Choose form radio and brand radio
        elif age == '' and form != '' and brand != '':
            products = Product.objects.filter(category=id, form__name=form, brand__name=brand)
            ages = list(Category.objects.filter(pk=pk, product__form__name = form, product__brand__name = brand).annotate(Count('product')).values_list('product__age__name', 'product__count').order_by('-product__count'))
            type = 3
            if len(ages) == 0:
                age_delete = True
            if len(ages) == 1 :
                age_disable = True
        # Choose form radio
        elif age == '' and brand == '' and form != '':
            products = Product.objects.filter(category=id, form__name=form)
            ages = list(Category.objects.filter(pk=pk, product__form__name = form).annotate(Count('product')).values_list('product__age__name', 'product__count').order_by('-product__count'))
            brands = list(Category.objects.filter(pk=pk, product__form__name = form).annotate(Count('product')).values_list('product__brand__name', 'product__count').order_by('-product__count'))
            type = 4
            if len(ages) == 0:
                age_delete = True
            if len(brands) == 0:
                brand_delete = True
            if len(ages) == 1 :
                age_disable = True
            if len(brands) == 1 :
                brand_disable = True
        # Choose age radio
        elif brand == '' and form == '' and age != '':
            products = Product.objects.filter(category=id, age__name=age)
            forms = list(Category.objects.filter(pk=pk, product__age__name = age).annotate(Count('product')).values_list('product__form__name', 'product__count').order_by('-product__count'))
            brands = list(Category.objects.filter(pk=pk, product__age__name = age).annotate(Count('product')).values_list('product__brand__name', 'product__count').order_by('-product__count'))
            type = 5
            if len(forms) == 0:
                form_delete = True
            if len(brands) == 0:
                brand_delete = True
            if len(forms) == 1 :
                form_disable = True
            if len(brands) == 1 :
                brand_disable = True
        # Choose form radio, age radio
        elif brand == '' and form != '' and age != '':
            products = Product.objects.filter(category=id, form__name=form, age__name=age)
            brands = list(Category.objects.filter(pk=pk, product__form__name = form, product__age__name = age).annotate(Count('product')).values_list('product__brand__name', 'product__count').order_by('-product__count'))
            type = 6
            if len(brands) == 0:
                brand_delete = True
            if len(brands) == 1 :
                brand_disable = True
        # Choose form radio, age radio and brand radio
        elif age != '' and form !='' and brand !='':
            products = Product.objects.filter(category=id, form__name=form, age__name=age, brand__name=brand)
            forms = list(Category.objects.filter(pk=pk, product__age__name = age, product__form__name = form, product__brand__name = brand).annotate(Count('product')).values_list('product__form__name', 'product__count').order_by('-product__count'))
            ages = list(Category.objects.filter(pk=pk, product__form__name = form, product__age__name = age, product__brand__name = brand).annotate(Count('product')).values_list('product__age__name', 'product__count').order_by('-product__count'))
            brands = list(Category.objects.filter(pk=pk, product__form__name = form, product__age__name = age, product__brand__name = brand).annotate(Count('product')).values_list('product__brand__name', 'product__count').order_by('-product__count'))
            type = 7

        context = {
            "products":products,
            "status":200
        }
        data = {}
        data['list'] = [render_to_string('medcare/block/brand_product_block.html',context=context, request=request),
            {
                'type': type,
                'forms':forms, 
                'ages':ages, 
                'brands':brands, 
                'brand_pk':id, 
                'form_delete': form_delete, 
                'age_delete':age_delete, 
                'brand_delete': brand_delete, 
                'brand_disable':brand_disable,
                'form_disable':form_disable,
                'age_disable':age_disable}
        ]
        return JsonResponse(data)
        
    return render(request,'medcare/category_product.html', context=context)   

@csrf_exempt 
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST or None)
        
        if form.is_valid():
            form.save()
            messages.success(request, _(f"Your account has been created! You can login now"))
            
            return redirect('login')
            
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile(request):
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        request.session['cart'] = cart_count
    else:
        request.session['cart'] = {}

    if request.method == "POST":
        if request.POST.get('password-reset'):
            form = PasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)
                messages.success(request, _("Your password was successfully updated."))
            else:
                # mess = ' '.join(str(e) for e in list(form.error_messages.values())[0:])
                mess = ' '.join(str(e) for e in [v[0] for k, v in form.errors.items()])
                if "This field is required"  in mess:
                    mess = "Please enter all required field."
                # print([v[0] for k, v in form.errors.items()])
                messages.warning(request, mess)

        else:
            UserEditForm = modelform_factory(
                User, 
                fields=('first_name', 'last_name', 'phone_number', 'address', 'city', 'country', 'zip_code'), 
            )
            form = UserEditForm(instance=request.user, data=request.POST or None)
            if form.is_valid():
                pattern = re.compile(PHONE_NUMBER_VALIDATOR)
                phone = form.cleaned_data['phone_number']
                if phone and not pattern.search(phone):
                    form.add_error('phone_number', _("Your phone number is invalid."))
                else:
                    form.save()
                    messages.success(request, _("Your information was succesfully updated."))
            messages.warning(request, form.errors)

        return redirect('profile')

    else:
        orders_list = Order.objects.filter(user=request.user).order_by('-status','created_at')
        categories = Category.objects.all()
        navbars = Navbar.objects.all()

        context = {
            "orders": orders_list,
            'navbars':navbars,
            'categories': categories
        }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def cart(request):
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        request.session['cart'] = cart_count
    else:
        request.session['cart'] = {}
    cart = Cart.objects.filter(user=request.user).select_related('product')
    categories = Category.objects.all()
    navbars = Navbar.objects.all()
    list_trending = list(Booking.objects.values_list('product', flat=True).annotate(count=Count('product')).order_by('-count'))
    trending = Product.objects.filter(pk__in=list_trending)[:8]
    stock_changed = False
    total_price = 0
    price_discount = 0
    for item in cart:
        in_stock = item.product.quantity

        if in_stock == 0:
            Cart.objects.filter(user=request.user, product=item.product).delete()
            stock_changed = True
        elif item.quantity > in_stock:
            messages.add_message(request, messages.INFO, _(f"{item.product.product_name} is out of stock limit, please decrease your product items"))
            stock_changed = True
        
        if (datetime.now(timezone.utc) < item.product.discount_expired):
            total_price += (item.product.price - (item.product.discount * item.product.price)/100) * item.quantity
            price_discount += (item.product.discount * item.product.price)/100 * item.quantity
        else:
            total_price += item.product.price * item.quantity
    
    context = {
        'navbars':navbars,
        'categories': categories,
        'cart': cart, 
        'changed':stock_changed, 
        'total':total_price, 
        'price_discount':price_discount, 
        'trending':trending
    }

    return render(request, 'medcare/cart.html', context=context)

@login_required
@transaction.atomic
def cart_add(request, pk):
    cart_form = CartForm(initial={'quantity': 0})

    if request.method == "POST" and request.is_ajax():
        cart_form = CartForm(request.POST)
    else:
        cart_form = 0

    product_get = Product.objects.filter(pk=pk).first()
    if product_get:
        product_stock = product_get.quantity
    else:
        product_stock = 0

    in_cart = Cart.objects.filter(user=request.user, product__pk=pk).first()
    if in_cart:
        cart_quantity = in_cart.quantity
    else:
        cart_quantity = 0
    
    if cart_form.is_valid():
        if int(cart_form.data["quantity"]) > 0 :
            if int(cart_form.data["quantity"]) + cart_quantity > product_stock:
                cart_count = Cart.objects.filter(user=request.user).count()
                request.session['cart'] = cart_count
                return JsonResponse({"status":"warning", "cart_count":cart_count, "message":_("Out of stock limit")})
            else:
                if in_cart:
                    in_cart.quantity = int(cart_form.data["quantity"]) + cart_quantity
                    in_cart.save()
                    cart_count = Cart.objects.filter(user=request.user).count()
                    request.session['cart'] = cart_count
                else:
                    product_new = cart_form.save(commit=False)
                    product_new = Cart(user=request.user, product=Product.objects.get(pk=pk), quantity=int(cart_form.data["quantity"]))
                    product_new.save()
                    cart_count = Cart.objects.filter(user=request.user).count()
                    request.session['cart'] = cart_count
                return JsonResponse({"status":"success", "cart_count":cart_count, "message":_("You added a product to your cart")})
        else:
            cart_count = Cart.objects.filter(user=request.user).count()
            request.session['cart'] = cart_count
            return JsonResponse({"status":"error", "cart_count":cart_count, "message":_("Please add product quantity more than 0")})
    else:
        cart_count = Cart.objects.filter(user=request.user).count()
        request.session['cart'] = cart_count
        return JsonResponse({"status":"error", "cart_count":cart_count, "message":_("Invalid input value")})

@login_required
@transaction.atomic
def increase_product_in_cart(request, pk):
    if request.is_ajax():
        product_get = Product.objects.filter(pk=pk).first()
        total_price = 0.0
        sum = 0.0
        price_discount = 0.0
        if product_get:
            product_stock = product_get.quantity
        else:
            product_stock = 0

        item = Cart.objects.filter(user=request.user, product__pk=pk).first()
        if item:
            cart_quantity = item.quantity
        else:
            cart_quantity = 0
        
        if cart_quantity + 1 > product_stock:
            return JsonResponse({"status":"warning","quantity":item.quantity, "message":_("Out of stock limit")})
        else:
            item.quantity = cart_quantity + 1
            item.save()

            if (datetime.now(timezone.utc) < item.product.discount_expired):
                total_price += (item.product.price - (item.product.discount * item.product.price)/100.0) * item.quantity
            else:
                total_price += item.product.price * item.quantity

            cart = Cart.objects.filter(user=request.user).select_related('product')
            for i in cart:
                if (datetime.now(timezone.utc) < i.product.discount_expired):
                    sum += (i.product.price - (i.product.discount * i.product.price)/100.0) * i.quantity
                    price_discount += (i.product.discount * i.product.price)/100.0 * i.quantity
                else:
                    sum += i.product.price * i.quantity

            return JsonResponse({"status":"success","quantity":item.quantity, "price_discount":format(price_discount,".2f"), "total":format(total_price,".2f"), "sum":format(sum,".2f"), "message":_('You added one more item of product to your cart')})

@login_required
@transaction.atomic
def decrease_product_in_cart(request, pk):
    if request.is_ajax():
        item = Cart.objects.filter(user=request.user, product__pk=pk).first()
        total_price = 0.0
        sum = 0.0
        price_discount = 0.0

        if item:
            cart_quantity = item.quantity
        else:
            cart_quantity = 0

        if cart_quantity > 0:
            item.quantity = cart_quantity - 1
            if item.quantity == 0 :
                item.delete()
                cart_count = Cart.objects.filter(user=request.user).count()
                request.session['cart'] = cart_count
                in_cart = Cart.objects.filter(user=request.user).values_list('product_id', flat=True)
                cart = Cart.objects.filter(user=request.user).select_related('product')
                for i in cart:
                    if (datetime.now(timezone.utc) < i.product.discount_expired):
                        sum += (i.product.price - (i.product.discount * i.product.price)/100.0) * i.quantity
                        price_discount += (i.product.discount * i.product.price)/100.0 * i.quantity
                    else:
                        sum += i.product.price * i.quantity
                return JsonResponse({"status":"success", "type":"del", "sum":format(sum,".2f"), "price_discount":format(price_discount,".2f"), "cart_count":cart_count,"message":_('You deleted product out of your cart'), "in_cart":list(in_cart)})
            else: 
                item.save()
                in_cart = Cart.objects.filter(user=request.user).values_list('product_id', flat=True)
                if (datetime.now(timezone.utc) < item.product.discount_expired):
                    total_price += (item.product.price - (item.product.discount * item.product.price)/100.0) * item.quantity
                else:
                    total_price += item.product.price * item.quantity

                cart = Cart.objects.filter(user=request.user).select_related('product')
                for i in cart:
                    if (datetime.now(timezone.utc) < i.product.discount_expired):
                        sum += (i.product.price - (i.product.discount * i.product.price)/100) * i.quantity
                        price_discount += (i.product.discount * i.product.price)/100.0 * i.quantity
                    else:
                        sum += i.product.price * i.quantity
                return JsonResponse({"status":"success","quantity":item.quantity,"type":"des", "price_discount":format(price_discount,".2f"), "sum":format(sum,".2f"), "total":format(total_price,".2f"),"message":_('You deleted one item of product out of your cart'), "in_cart":list(in_cart)})
        else:
            return JsonResponse({"status":"error", "message":_('Cart quantity must be more than 0')})

@login_required
@transaction.atomic
def remove_from_cart(request, pk):
    if request.is_ajax():
        sum = 0.0
        price_discount = 0.0
        Cart.objects.filter(user=request.user, product__pk=pk).delete()
        cart_count = Cart.objects.filter(user=request.user).count()
        request.session['cart'] = cart_count
        in_cart = Cart.objects.filter(user=request.user).values_list('product_id', flat=True)
        cart = Cart.objects.filter(user=request.user).select_related('product')
        for i in cart:
            if (datetime.now(timezone.utc) < i.product.discount_expired):
                sum += (i.product.price - (i.product.discount * i.product.price)/100) * i.quantity
                price_discount += (i.product.discount * i.product.price)/100.0 * i.quantity
            else:
                sum += i.product.price * i.quantity
        
        return JsonResponse({"status":"success", "message": _('Product has been removed from your cart'), "in_cart":list(in_cart), "cart_count":cart_count,"price_discount":format(price_discount,".2f"), "sum":format(sum,".2f")})

@login_required
@transaction.atomic
def checkout(request):
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        request.session['cart'] = cart_count
    else:
        request.session['cart'] = {}
    categories = Category.objects.all()
    navbars = Navbar.objects.all()
    cart = Cart.objects.filter(user=request.user).select_related('product')
    coupons = Coupon.objects.filter(usecoupon__used=False, usecoupon__saved=True, coupon_expired__gt=datetime.now(timezone.utc)).order_by('-usecoupon__applied')
    coupon_applied = UseCoupon.objects.filter(user=request.user, applied=True, used=False).first()
    items_total = 0
    price_discount = 0
    total_price = 0

    for item in cart:
        item_quantity = item.quantity
        product_stock = item.product.quantity

        if product_stock == 0:
            item.delete()
            items_total += item.product.price * item.quantity
        elif item_quantity > product_stock:
            messages.add_message(request, messages.INFO, _(f"{item.product.product_name} is out of stock limit, please decrease your product items in your cart"))
            return redirect('/medcare/cart')
        else:
            if (datetime.now(timezone.utc) < item.product.discount_expired):
                items_total += (item.product.price - (item.product.discount * item.product.price)/100) * item.quantity
                price_discount += (item.product.discount * item.product.price)/100 * item.quantity
            else:
                items_total += item.product.price * item.quantity

    # Apply code coupon
    coupon_form = CouponForm()

    if request.method == "POST" and request.is_ajax() and request.POST.get('action') == 'codeCoupon':
        coupon_code = request.POST.get('code', None)
        all_codes = Coupon.objects.all().values_list('code', flat=True)
        used_codes = Coupon.objects.filter(usecoupon__user=request.user,usecoupon__used=True).values_list('code', flat=True)
        already_applied_code = Coupon.objects.filter(usecoupon__user=request.user,usecoupon__applied=True).values_list('code', flat=True)
        
        if coupon_code in all_codes:
            if coupon_code not in already_applied_code:
                if coupon_code not in used_codes: 
                    coupon = Coupon.objects.filter(code=coupon_code).first()
                    if (datetime.now(timezone.utc) < coupon.coupon_expired):
                        if (items_total > coupon.minimum_order):
                            coupon_obj = Coupon.objects.filter(code=coupon_code).first()
                            total_price = items_total - ((coupon_obj.value*items_total)/100)
                            coupon_discount = (coupon_obj.value*items_total)/100

                            if coupon_applied:
                                old_applied_coupon = UseCoupon.objects.get(user=request.user, applied=True, id=coupon_applied.id)
                                old_applied_coupon.applied = False
                                old_applied_coupon.save()

                            coupon_available = UseCoupon.objects.filter(user=request.user, coupon=coupon.id).first()

                            if coupon_available:
                                applied_coupon = UseCoupon.objects.get(user=request.user, id=coupon_available.id)
                                applied_coupon.applied = True
                                applied_coupon.save()
                                return JsonResponse({"status":"success", "message":"Applied coupon code sucessfully", "applied_coupon":applied_coupon.coupon.title, "pk": applied_coupon.coupon.pk , "total":round(total_price, 2), "coupon_discount":round(coupon_discount, 2),"type":"success"})
                            else:
                                applied_coupon = UseCoupon(user=request.user, saved=False, used= False, applied=True, coupon=Coupon.objects.get(id=coupon.id))
                                applied_coupon.save()
                                return JsonResponse({"status":"success", "message":"Applied coupon code sucessfully", "applied_coupon":applied_coupon.coupon.title, "pk": applied_coupon.coupon.pk ,"total":round(total_price, 2), "coupon_discount":round(coupon_discount, 2),"type":"success"})
                        else:
                            return JsonResponse({"status":"warning", "message":"Sorry, you can not use this coupon. Please check the coupon conditions"})
                    else:
                        return JsonResponse({"status":"warning", "message":"This coupon code was expired"})
                else:
                    return JsonResponse({"status":"warning", "message":"You have already used this coupon code"})
            else:
                return JsonResponse({"status":"warning", "message":"You have already applied this coupon code"})
        else:
            return JsonResponse({"status":"error", "message":"Unvalid coupon code"})

    # Apply saved coupon 
    if request.method == "POST" and request.is_ajax() and request.POST.get('action') == 'applyCoupon':
        coupon_id = request.POST.get('id', None)
        coupon_obj = Coupon.objects.filter(pk=coupon_id).first()
        total_price = items_total - ((coupon_obj.value*items_total)/100)
        coupon_discount = (coupon_obj.value*items_total)/100

        coupon_available = UseCoupon.objects.filter(user=request.user, coupon=coupon_id).first()

        if coupon_applied:
            old_applied_coupon = UseCoupon.objects.get(user=request.user, applied=True, id=coupon_applied.id)
            old_applied_coupon.applied = False
            old_applied_coupon.save()

        if coupon_available:
            applied_coupon = UseCoupon.objects.get(user=request.user, id=coupon_available.id)
            applied_coupon.applied = True
            applied_coupon.save()
        else:
            applied_coupon = UseCoupon(user=request.user, saved=False, used= False, applied=True, coupon=Coupon.objects.get(id=coupon_id))
            applied_coupon.save()
        
        return JsonResponse({"status":200, "items_total":round(items_total,2),"total":round(total_price, 2), "coupon_discount":round(coupon_discount, 2), "applied_coupon":applied_coupon.coupon.title, "pk":applied_coupon.coupon_id})

    # Remove applied coupon 
    if request.method == "POST" and request.is_ajax() and request.POST.get('action') == 'removeCoupon':
        coupon_id = request.POST.get('id', None)
        coupon = UseCoupon.objects.get(user=request.user, coupon_id=coupon_id)
        coupon.applied = False
        coupon.save()

        return JsonResponse({"status":200, "items_total":format(items_total,".1f")})

    if coupon_applied:
        coupon_discount = (coupon_applied.coupon.value*items_total)/100
        total_pricee = items_total - coupon_discount
    else:
        coupon_discount = 0
        total_pricee = items_total

    # Checkout
    if request.method == "POST" and 'checkout' in request.POST:
        shipping_address = request.POST.get('shipping_address','')
        phone_number = request.POST.get('phone_number','')

        if shipping_address and phone_number:
            order = Order(user=request.user, shipping_address=shipping_address, phone_number=phone_number, total_price=total_pricee, status='W')

            if order:
                order.save()
                if coupon_applied:
                    coupon_applied.used = True
                    coupon_applied.applied = False
                    coupon_applied.save()

                context = {
                    'system': "Medcare team",
                    'order_id': order.id,
                    'username': order.user.username,
                    'date': order.created_at,
                    'orders': cart,
                    'total': order.total_price,
                    'host': settings.HOST,
                }
                messages.add_message(request, messages.INFO, _('Order is waiting for being approved by admin! Please wait the approve message!'))
                message = get_template('messages/order_success_message.html').render(context)
                msg = EmailMessage(f'[Medcare] New order #{order.id} have been made, please check waiting order.',message, settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER],)
                msg.content_subtype = "html"  
                msg.send()
            
                # Xử lý giảm số hàng của sản phẩm trong kho sau khi order
                for item in cart:
                    order_detail = Booking(order=order, quantity=item.quantity, product=Product.objects.get(id=item.product.pk))
                    order_detail.save()
                    item.product.quantity -= item.quantity
                    item.product.save()
                # Xử lý làm rỗng giỏ hàng
                Cart.objects.filter(user=request.user).delete()
                request.session['cart'] = {}
                return redirect('/medcare/')
            else:
                return JsonResponse({"status":"error", "message":"Order is invalid, try again!"})
        else:
            return JsonResponse({"status":"error", "message":"Shipping address or phone number is invalid!"})
    else:
        shipping_address = ''
        phone_number = ''

    context1 = {
        'cart': cart, 
        'items_total':items_total,
        'total': round(total_pricee, 1), 
        'coupons':coupons, 
        'coupon_applied':coupon_applied, 
        'coupon_discount':round(coupon_discount,1),
        'coupon_form':coupon_form,
        'navbars':navbars,
        'categories':categories
    }

    return render(request, 'medcare/checkout.html', context=context1)

@login_required
def report_add(request, pk):
    if request.method == "POST" and request.is_ajax() and request.POST.get('action') == 'report':
        title = request.POST.get('title','')
        content = request.POST.get('content','')
        review_id = request.POST.get('review_id', None)

        if title and content and review_id:
            review = Review.objects.get(id=review_id)
            report = Report(user=request.user, title=title, content=content, review=review)

            if report:
                report.save()
                return JsonResponse({"status":"success", "message":"Report is submitted successfully"})
            else:
                return JsonResponse({"status":"error", "message":"Report is invalid, try again!"})
        else:
            title = ''
            content = ''
            review_id = None
            return JsonResponse({"status":"error", "message":"Title or content is invalid!"})

def coupon_event(request):
    hot_coupon = Coupon.objects.filter(minimum_order=0)
    time_coupon = Coupon.objects.filter(coupon_expired__isnull=False)
    list_trending = list(Booking.objects.values_list('product', flat=True).annotate(count=Count('product')).order_by('-count'))
    trending = Product.objects.filter(pk__in=list_trending)[:8]
    hot_deal = Product.objects.filter(discount_expired__gte=datetime.now(timezone.utc))
    categories = Category.objects.all()
    navbars = Navbar.objects.all()
    if request.user.is_authenticated:
        saved_coupons = UseCoupon.objects.filter(user=request.user, saved=True).values_list('coupon_id', flat=True)
        used_coupons = UseCoupon.objects.filter(user=request.user, used=True).values_list('coupon_id', flat=True)
    else:
        saved_coupons = None
        used_coupons = None

    context = {
        'categories': categories,
        'navbars': navbars,
        'hot_coupon': hot_coupon,
        'time_coupon': time_coupon,
        'saved_coupons': saved_coupons,
        'used_coupons': used_coupons,
        'trending':trending,
        'hot_deal':hot_deal
    }
    return render(request, 'medcare/coupon_event.html', context=context)

@login_required
def request_get(request):
    request_form = RequestForm()
    categories = Category.objects.all()
    navbars = Navbar.objects.all()
    if request.user.is_authenticated:
        requests =  Request.objects.filter(user=request.user).order_by('-created_at')
    else:
        requests = {}

    if request.method == 'POST' and request.is_ajax() and request.POST.get('action') == 'filter':
        type = request.POST.get('type', None)
        if type == 'newest':
            requests =  Request.objects.filter(user=request.user).order_by('-created_at')
            context = {
                "requests":requests,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/request_list_block.html',context=context, request=request)
            return JsonResponse(data)
        elif type == 'oldest':
            requests =  Request.objects.filter(user=request.user).order_by('created_at')
            context = {
                "requests":requests,
                "status":200
            }
            data = {}
            data['list'] = render_to_string('medcare/block/request_list_block.html',context=context, request=request)
            return JsonResponse(data)

    context = {
        'request_form':request_form,
        'categories': categories,
        'navbars': navbars,
        'requests': requests,
        'count': requests.count,
    }

    return render(request, 'medcare/request_list.html', context=context)

@login_required
@transaction.atomic
def request_action(request):
    # Add request
    if request.method == "POST" and request.is_ajax() and request.POST.get('action') == 'addRequest':
        title = request.POST.get('title', None)
        content = request.POST.get('content', None)

        if title and content:
            rq = Request(user=request.user, title=title, content=content)
            if rq:
                rq.save()
                requests =  Request.objects.filter(user=request.user).order_by('-created_at')
                context = {
                    "requests":requests,
                    "status":200
                }
                data = {}
                data['list'] = [render_to_string('medcare/block/request_list_block.html',context=context, request=request),
                    {
                        'status':'success', 
                        'message':'Request is sent successfully. We will response to you soon. Keep following here.',
                        'count':requests.count(),
                    }]
                return JsonResponse(data)
            else:
                return JsonResponse({"status":"error", "message":"Request is invalid, try again!"})
        else:
            title = ''
            content = ''
            return JsonResponse({"status":"error", "message":"Title or content is invalid!"})

    # Remove request
    if request.method == "POST" and request.is_ajax() and request.POST.get('action') == 'removeRequest':
        request_id = request.POST.get('request_id', None)
        if request_id:
            rq = Request.objects.filter(user=request.user, id=request_id).first()
            if rq:
                if rq.status == 'Sent':
                    rq.delete()
                    requests =  Request.objects.filter(user=request.user).order_by('-created_at')
                    context = {
                        "requests":requests,
                        "status":200
                    }
                    data = {}
                    data['list'] = [render_to_string('medcare/block/request_list_block.html',context=context, request=request),
                    {
                        'status':'success', 
                        'message':'Request was removed successfully.',
                        'count':requests.count(),
                    }]
                    return JsonResponse(data)
                else:
                    data = {}
                    data['list'] = [None,
                    {
                        "status":"error", 
                        "message":"You do not have permission to remove this request."
                    }]
                    return JsonResponse(data)
            else:
                data = {}
                data['list'] = [None,
                {
                    "status":"error", 
                    "message":"Request is invalid."
                }]
                return JsonResponse(data)
        else:
            request_id = None
            data = {}
            data['list'] = [None,
            {
                "status":"error", 
                "message":"Request UUID is invalid!"
            }]
            return JsonResponse(data)

@login_required
@transaction.atomic
def order_remove(request, pk):
    if request.is_ajax():
        Order.objects.filter(user=request.user, id=pk).delete()

        bookings = Booking.objects.filter(order=pk).select_related('product')
        for item in bookings:
            item.product.quantity += item.quantity
            item.product.save()

        return JsonResponse({"status":"success", "message":"Order was removed successfully."})
   
@login_required
def order_detail(request, pk):
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        request.session['cart'] = cart_count
    else:
        request.session['cart'] = {}

    order = Order.objects.get(pk=pk)
    detail = Booking.objects.filter(order=pk).select_related('product')
    categories = Category.objects.all()
    navbars = Navbar.objects.all()

    context = {
        'id': pk, 
        'status': order.status, 
        'detail': detail, 
        'total': order.total_price,
        'categories': categories,
        'navbars': navbars
    }

    return render(request, 'medcare/order_detail.html', context=context)

@login_required
@transaction.atomic
def review_add(request, pk):
    product = Product.objects.filter(id=pk).first()
    rv = Review.objects.filter(user=request.user, product__pk=pk).first()
    reviewed = True if rv else False

    if request.method == "POST" and request.is_ajax():
        review_form = ReviewForm(request.POST)
        if (reviewed == False):
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
                results = serializers.serialize('json', [ review, ])
                rvdate = review.created_at
                date = rvdate.strftime('%b %d, %Y, %I:%M %p').replace( 'AM', 'a.m.' ).replace( 'PM', 'p.m.' )

                count2 = Review.objects.filter(product__pk=pk).count()
                five_stars = Review.objects.filter(product__pk=pk, rate=5).count()
                four_stars = Review.objects.filter(product__pk=pk, rate=4).count()
                three_stars = Review.objects.filter(product__pk=pk, rate=3).count()
                two_stars = Review.objects.filter(product__pk=pk, rate=2).count()
                one_star = Review.objects.filter(product__pk=pk, rate=1).count()

                average = round(((5*five_stars + 4*four_stars + 3*three_stars + 2*two_stars + 1*one_star) / count2),1)
                five_percentage = int((five_stars/count2)*100)
                four_percentage = int((four_stars/count2)*100)
                three_percentage = int((three_stars/count2)*100)
                two_percentage = int((two_stars/count2)*100)
                one_percentage = int((one_star/count2)*100)

                context = {
                    "status":200, 
                    "results": results, 
                    "first_name": review.user.first_name, 
                    "last_name":review.user.last_name, 
                    "created":date,
                    "average":average,
                    "five_percentage":five_percentage,
                    "four_percentage":four_percentage,
                    "three_percentage":three_percentage,
                    "two_percentage":two_percentage,
                    "one_percentage":one_percentage,
                    "count2": count2,
                    "status":"success",
                    "message":_("Your review was added successfully")
                }

                return JsonResponse(data=context)  
            else:
                errors = review_form.errors.as_json()
                return JsonResponse({"errors": errors,  "status":400})
        else:
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.id = rv.id
                review.product = product
                review.user = request.user
                review.save()
                results = serializers.serialize('json', [ review, ])
                rvdate = review.created
                date = rvdate.strftime('%b %d, %Y, %I:%M %p').replace( 'AM', 'a.m.' ).replace( 'PM', 'p.m.' )

                count2 = Review.objects.filter(product__pk=pk).count()
                five_stars = Review.objects.filter(product__pk=pk, rate=5).count()
                four_stars = Review.objects.filter(product__pk=pk, rate=4).count()
                three_stars = Review.objects.filter(product__pk=pk, rate=3).count()
                two_stars = Review.objects.filter(product__pk=pk, rate=2).count()
                one_star = Review.objects.filter(product__pk=pk, rate=1).count()

                average = round(((5*five_stars + 4*four_stars + 3*three_stars + 2*two_stars + 1*one_star) / count2),1)
                five_percentage = int((five_stars/count2)*100)
                four_percentage = int((four_stars/count2)*100)
                three_percentage = int((three_stars/count2)*100)
                two_percentage = int((two_stars/count2)*100)
                one_percentage = int((one_star/count2)*100)

                context = {
                    "status":200, 
                    "edit": True,
                    "results": results, 
                    "first_name": review.user.first_name, 
                    "last_name":review.user.last_name, 
                    "created":date, 
                    "id": review.id,
                    "average":average,
                    "five_percentage":five_percentage,
                    "four_percentage":four_percentage,
                    "three_percentage":three_percentage,
                    "two_percentage":two_percentage,
                    "one_percentage":one_percentage,
                    "count2": count2,
                    "status":"success",
                    "message":_("Your review was edited successfully")
                }

                return JsonResponse(data=context)  
            else:
                errors = review_form.errors.as_json()
                return JsonResponse({"errors": errors,  "status":400})
    else:
        review_form = ReviewForm(user=request.user, product=product)
        
        context = {
            'review_form': review_form
        }
        return render(request, 'medcare/product_detail.html', context=context)

# admin dashboard
@login_required
def dashboard(request):
    today_orders = Order.objects.filter(created_at__gt=timezone.localtime()-timedelta(days=1))
    yesterday_orders =  Order.objects.filter(Q(created_at__lt=timezone.localtime()-timedelta(days=1)) | Q(created_at__gt=timezone.localtime()-timedelta(days=2)))
    today_orders_percentage = ((today_orders.count()-yesterday_orders.count())/yesterday_orders.count())*100 
    month_orders = Order.objects.filter(created_at__gt=timezone.localtime()-timedelta(weeks=4))
    last_month_orders = Order.objects.filter(created_at__lt=timezone.localtime()-timedelta(weeks=4), created_at__gt=timezone.localtime()-timedelta(weeks=8))
    
    if last_month_orders.count() != 0:
        month_orders_percentage = ((month_orders.count()-last_month_orders.count())/last_month_orders.count())*100
    else:
        month_orders_percentage = 0.0

    new_users = User.objects.filter(is_superuser=False, is_admin= False, is_staff=False, created_at__gt=timezone.localtime()-timedelta(weeks=4))
    last_month_users = User.objects.filter(is_superuser=False, is_admin= False, is_staff=False, created_at__lt=timezone.localtime()-timedelta(weeks=4), created_at__gt=timezone.localtime()-timedelta(weeks=8))

    if last_month_users.count() != 0:
        month_users_percentage = ((new_users.count()-last_month_users.count())/last_month_users.count())*100
    else:
        month_users_percentage = 0.0

    total_orders = Order.objects.all()
    popular_product_list = list(Booking.objects.values_list('product', flat=True).annotate(count=Count('product')).order_by('-count'))
    popular_products = Product.objects.filter(pk__in=popular_product_list)[:10]
    most_viewed_news = News.objects.order_by('-viewed')[:10]

    context = {
        "today_orders": today_orders.count(),
        "today_orders_percentage": today_orders_percentage,
        "month_orders": month_orders.count(),
        "month_orders_percentage": month_orders_percentage,
        "new_users":new_users.count(),
        "month_users_percentage": month_users_percentage,
        "total_orders":total_orders.count(),
        "popular_products":popular_products,
        "most_viewed_news":most_viewed_news,
    }

    return render(request, 'admin/content/dashboard.html', context=context)

@login_required
def table(request):
    return render(request, 'admin/content/tables.html')

@login_required
def order_manage(request):
    orders = Order.objects.order_by('-status','-created_at')
    paginator = Paginator(orders, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "order_list":orders,
        "page_obj":page_obj,
    }

    return render(request, 'admin/content/order_manage.html',context=context)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt 
@login_required
@transaction.atomic
@permission_required('medcare.can_mark_returned', raise_exception=True)
def check_order_status(request, pk):
    if request.method == 'POST' and request.is_ajax():
        status = request.POST.get('status','W')
    else:
        status = 'W'
    
    order = Order.objects.filter(id=pk).first()
    order.status = status
    order.save()

    detail = Booking.objects.filter(order=pk).select_related('product')

    context = {
        'system': "Django website team",
        'order_id': order.id,
        'username': order.user.username,
        'date': order.created_at,
        'orders': detail,
        'total': order.total_price,
        'host': settings.HOST,
    }

    if status == 'A':
        message = get_template('messages/order_accepted_message.html').render(context)
        msg = EmailMessage(f'[Medcare] Your order #{pk} have been accepted.',message, settings.EMAIL_HOST_USER, [order.user.email],)
        msg.content_subtype = "html"  
        msg.send()
    elif  status == 'R':
        message = get_template('messages/order_rejected_message.html').render(context)
        msg = EmailMessage(f'[Medcare] Your order #{pk} have been rejected.',message, settings.EMAIL_HOST_USER, [order.user.email],)
        msg.content_subtype = "html"  
        msg.send()

    context1 = {
        "order":order,
        "status":200
    }
    data = {}
    data['list'] = [render_to_string('admin/block/order_check_block.html',context=context1, request=request),
    {
        'status':'success', 
        'message':'Order status was updated successfully.',
        "check":order.status
    }]

    return JsonResponse(data)

@login_required
def booking_detail(request, pk):
    order = Order.objects.get(pk=pk)
    detail = Booking.objects.filter(order=pk).select_related('product')

    return render(request, 'admin/content/booking_detail.html', {'id': pk, 'status': order.status, 'detail': detail, 'total': order.total_price})

@login_required
def product_manage(request):
    products = Product.objects.all()
 
    product_paginator = Paginator(products, 8)
    product_page_number = request.GET.get('page')
    product_page_obj = product_paginator.get_page(product_page_number)

    context = {
        'product_list': products,
        'product_paginator': product_paginator,
        'product_page_obj': product_page_obj,
    }

    return render(request, 'admin/content/product_manage.html',context=context)

@login_required
def category_manage(request):
    categories = Category.objects.all()
    category_paginator = Paginator(categories, 8)
    category_page_number =  request.GET.get('page')
    category_page_obj = category_paginator.get_page(category_page_number)

    context = {
        'category_list': categories,
        'category_paginator': category_paginator,
        'category_page_obj': category_page_obj,
    }

    return render(request, 'admin/content/category_manage.html',context=context)

@login_required
def category_detail(request, pk):
    category = Category.objects.filter(id=pk).first()
    object = Category.objects.get(id=pk)
    navbars = Navbar.objects.all()
    
    if request.method == 'POST' and request.is_ajax():
        # F = request.FILES
        # print("form The uploaded file is:",F)     
        CategoryEditForm = modelform_factory(
            Category, 
            fields=('name', 'image', 'advert_image', 'navbar', 'is_popular'), 
        )
        form = CategoryEditForm(instance=object, data=request.POST or None)
        if form.is_valid():
            form.save()
            return JsonResponse({"status":"success", "message":"Update category information successfully."})
        else:
            return JsonResponse({"status":"danger", "message":form.errors})

    context = {
        'category': category,
        'navbars': navbars,
    }

    return render(request, 'admin/content/category_detail.html', context=context)

@login_required
def brand_manage(request):
    brands = Brand.objects.all()
    brand_paginator = Paginator(brands, 8)
    brand_page_number =  request.GET.get('page')
    brand_page_obj = brand_paginator.get_page(brand_page_number)

    context = {
        'brand_list': brands,
        'brand_paginator': brand_paginator,
        'brand_page_obj': brand_page_obj,
    }

    return render(request, 'admin/content/brand_manage.html',context=context)

@login_required
def user_manage(request):
    users = User.objects.all()
    user_paginator = Paginator(users, 8)
    user_page_number =  request.GET.get('page')
    user_page_obj = user_paginator.get_page(user_page_number)

    context = {
        'user_list': users,
        'user_paginator': user_paginator,
        'user_page_obj': user_page_obj,
    }

    return render(request, 'admin/content/user_manage.html',context=context)

@login_required
def user_detail(request, pk):
    user = User.objects.filter(id=pk).first()

    if request.method == 'POST' and request.is_ajax():
        UserEditForm = modelform_factory(
            User, 
            fields=('username','first_name', 'last_name', 'phone_number', 'address', 'city', 'country', 'zip_code'), 
        )
        form = UserEditForm(instance=request.user, data=request.POST or None)
        if form.is_valid():
            pattern = re.compile(PHONE_NUMBER_VALIDATOR)
            phone = form.cleaned_data['phone_number']
            if phone and not pattern.search(phone):
                return JsonResponse({"status":"danger", "message":"Phone number is invalid."})
            else:
                form.save()
                return JsonResponse({"status":"success", "message":"Update user information successfully."})
        else:
            return JsonResponse({"status":"danger", "message":form.errors})

    context = {
        'user': user,
    }

    return render(request, 'admin/content/user_detail.html', context=context)

@login_required
def coupon_manage(request):
    coupons = Coupon.objects.all()
    coupon_paginator = Paginator(coupons, 8)
    coupon_page_number =  request.GET.get('page')
    coupon_page_obj = coupon_paginator.get_page(coupon_page_number)

    context = {
        'coupon_list': coupons,
        'coupon_paginator': coupon_paginator,
        'coupon_page_obj': coupon_page_obj,
    }

    return render(request, 'admin/content/coupon_manage.html',context=context)

@login_required
def request_manage(request):
    requests = Request.objects.all()
    request_paginator = Paginator(requests, 8)
    request_page_number =  request.GET.get('page')
    request_page_obj = request_paginator.get_page(request_page_number)

    context = {
        'request_list': requests,
        'request_paginator': request_paginator,
        'request_page_obj': request_page_obj,
    }

    return render(request, 'admin/content/request_manage.html',context=context)

@login_required
def report_manage(request):
    reports = Report.objects.all()
    report_paginator = Paginator(reports, 8)
    report_page_number =  request.GET.get('page')
    report_page_obj = report_paginator.get_page(report_page_number)

    context = {
        'report_list': reports,
        'report_paginator': report_paginator,
        'report_page_obj': report_page_obj,
    }

    return render(request, 'admin/content/report_manage.html',context=context)

@login_required
def news_manage(request):
    news = News.objects.all()
    news_paginator = Paginator(news, 8)
    news_page_number =  request.GET.get('page')
    news_page_obj = news_paginator.get_page(news_page_number)

    context = {
        'news_list': news,
        'news_paginator': news_paginator,
        'news_page_obj': news_page_obj,
    }

    return render(request, 'admin/content/news_manage.html',context=context)
