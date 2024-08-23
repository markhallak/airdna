from django.urls import path
from .views import searchForPropertiesUsingZipCode, showSearchPage

urlpatterns = [
    path('searchForPropertiesUsingZipCode', searchForPropertiesUsingZipCode, name='searchForPropertiesUsingZipCode'),
    path('', showSearchPage, name='showSearchPage')
]
