from django.contrib import admin
from django.urls import path
from carrierservice import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('api/track/', views.Track_shipment, name='track'),
    path('api/package/<str:tracking_number>/', views.Get_package, name='get_package'),
    path('api/packages/', views.List_packages, name='list_packages'),
]
