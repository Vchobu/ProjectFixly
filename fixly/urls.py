# URLs used for the project

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('fixly-admin/', include('core.urls_admin')),
    path('tenant/', include('core.urls_tenant')),
    path('contractor/', include('core.urls_contractor')),
]

# Debug mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
