from django.contrib.auth.views import LogoutView
from django.urls import path

from .forms import StyledAuthenticationForm
from .views import (
    UserLoginView,
    about,
    dashboard,
    delete_record,
    detect,
    history,
    landing,
    signup,
    update_record,
)


urlpatterns = [
    path('', landing, name='landing'),
    path('about/', about, name='about'),
    path(
        'login/',
        UserLoginView.as_view(authentication_form=StyledAuthenticationForm),
        name='login',
    ),
    path('signup/', signup, name='signup'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('detect/', detect, name='detect'),
    path('history/', history, name='history'),
    path('history/<int:pk>/update/', update_record, name='update_record'),
    path('history/<int:pk>/delete/', delete_record, name='delete_record'),
]
