from django.contrib import admin
from .models import Book, Reader, IssueBook

admin.site.register(Book)
admin.site.register(Reader)
admin.site.register(IssueBook)
