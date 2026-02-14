from django.contrib import admin
from django.urls import path
from library_app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home,name='home'),
    path('change-membership/<uuid:reader_id>/', views.change_membership, name='change_membership'),


    path('login/', views.login_view, name='login'),
    path('staff_logout/', views.staff_logout, name='staff_logout'),

    path('staff_page/', views.staff_page, name='staff_page'),

    path('category/', views.category, name='category'),
    path('delete_category/<int:id>/', views.delete_category, name='delete_category'),

    path('add_book/', views.add_book, name='add_book'),
    path('view_book/', views.view_book, name='view_book'),  # 👈 VIEW + UPDATE + DELETE

    path('add_reader/', views.add_reader, name='add_reader'),
    path('view_reader/', views.view_reader, name='view_reader'),

    path('issue_book/', views.issue_book, name='issue_book'),
    path('return-book/', views.return_book, name='return_book'),

    path('change-membership/<uuid:reader_id>/',views.change_membership,name='change_membership'),

    path('reader-history/<uuid:reader_id>/', views.reader_history, name='reader_history'),
    path('active-readers/', views.active_readers, name='active_readers'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)