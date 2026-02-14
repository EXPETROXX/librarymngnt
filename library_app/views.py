from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from uuid import UUID
from django.views.decorators.cache import never_cache


from .models import Category, Book, Reader, IssueBook


# ---------------- HOME ----------------
def home(request):
    return render(request, 'home.html')


# ---------------- LOGIN ----------------
def login_view(request):
    # If already logged in, redirect to staff page
    if request.user.is_authenticated:
        return redirect('staff_page')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            messages.error(request, "Invalid username or password")
            return redirect('login')

        if not user.is_active:
            messages.error(request, "Your account is inactive")
            return redirect('login')

        if not user.is_staff:
            messages.error(request, "You are not authorised to access staff panel")
            return redirect('login')

        # ✅ SUCCESS
        auth_login(request, user)
        messages.success(request, f"Welcome {user.username}")
        return redirect('staff_page')

    return render(request, 'login.html')

# ---------------- LOGOUT ----------------
@login_required(login_url='/login/')
@never_cache
def staff_logout(request):
    logout(request)
    request.session.flush()
    return redirect('login')


# ---------------- STAFF PAGE ----------------
@login_required(login_url='/login/')
@never_cache
def staff_page(request):
    if not request.user.is_staff:
        return redirect('login')
    return render(request, 'staff_page.html')


# ---------------- CATEGORY ----------------
@login_required(login_url='/login/')
@never_cache
def category(request):
    if not request.user.is_staff:
        return redirect('login')

    data = Category.objects.all()

    if request.method == 'POST':
        cat = request.POST.get('cat').strip()

        if Category.objects.filter(name__iexact=cat).exists():
            messages.error(request, "Category already exists")
        else:
            Category.objects.create(name=cat.title())
            messages.success(request, "Category added successfully")

        return redirect('category')

    return render(request, 'category.html', {'data': data})


@login_required(login_url='/login/')
def delete_category(request, id):
    if not request.user.is_staff:
        return redirect('login')

    Category.objects.filter(id=id).delete()
    return redirect('category')


# ---------------- ADD BOOK ----------------
@login_required(login_url='/login/')
@never_cache
def add_book(request):
    if not request.user.is_staff:
        return redirect('login')

    recent_book = None
    categories = Category.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        author = request.POST.get('author')
        ubno = request.POST.get('ubno')
        category = request.POST.get('category')
        total_copies = int(request.POST.get('total_copies'))

        if Book.objects.filter(ubno=ubno).exists():
            messages.error(request, "Book already exists")
        else:
            recent_book = Book.objects.create(
                title=title,
                author=author,
                ubno=ubno,
                category_id=category,
                total_copies=total_copies,
                available_copies=total_copies
            )
            messages.success(request, "Book added successfully")

    return render(request, 'add_book.html', {
        'cat_data': categories,
        'recent_book': recent_book
    })


# ---------------- VIEW BOOK ----------------
@login_required(login_url='/login/')
@never_cache
def view_book(request):
    if not request.user.is_staff:
        return redirect('login')

    if request.method == 'POST' and 'update_book' in request.POST:
        book = get_object_or_404(Book, id=request.POST.get('book_id'))
        new_ubno = request.POST.get('ubno')

        if Book.objects.exclude(id=book.id).filter(ubno=new_ubno).exists():
            messages.error(request, "Book ID already exists")
            return redirect('view_book')

        book.title = request.POST.get('title')
        book.author = request.POST.get('author')
        book.ubno = new_ubno
        book.category_id = request.POST.get('category')
        book.total_copies = int(request.POST.get('total_copies'))
        book.save()

        messages.success(request, "Book updated successfully")
        return redirect('view_book')

    if request.method == 'POST' and 'delete_book' in request.POST:
        book_id = request.POST.get('book_id')

        if IssueBook.objects.filter(book_id=book_id, is_returned=False).exists():
            messages.error(request, "Cannot delete book. It is currently issued.")
            return redirect('view_book')

        Book.objects.filter(id=book_id).delete()
        messages.success(request, "Book deleted successfully")
        return redirect('view_book')

    return render(request, 'view_book.html', {
        'book_data': Book.objects.all(),
        'categories': Category.objects.all()
    })


# ---------------- ADD READER ----------------
@login_required(login_url='/login/')
@never_cache
def add_reader(request):
    if not request.user.is_staff:
        return redirect('login')

    if request.method == 'POST':
        name = request.POST.get('reader_name')
        phone = request.POST.get('number')
        email = request.POST.get('email')
        address = request.POST.get('address')

        if Reader.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already exists")
            return redirect('add_reader')

        if Reader.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect('add_reader')

        Reader.objects.create(
            name=name,
            phone=phone,
            email=email,
            address=address
        )

        messages.success(request, f"Reader '{name}' added successfully")
        return redirect('add_reader')

    return render(request, 'add_reader.html')


# ---------------- VIEW READER ----------------
@login_required(login_url='/login/')
@never_cache
def view_reader(request):
    query = request.GET.get('q')
    readers = Reader.objects.all()

    if query:
        readers = readers.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        )

    return render(request, 'view_reader.html', {
        'reader_data': readers,
        'query': query
    })


# ---------------- ISSUE BOOK ----------------
@login_required(login_url='/login/')
@never_cache
def issue_book(request):
    if not request.user.is_staff:
        return redirect('login')

    reader = None
    readers = []
    books = []
    issued_books = []

    reader_q = request.GET.get('reader_q')
    book_q = request.GET.get('book_q')
    reader_id = request.GET.get('reader_id')

    if reader_q:
        readers = Reader.objects.filter(
            Q(name__icontains=reader_q) |
            Q(phone__icontains=reader_q) |
            Q(email__icontains=reader_q)
        )

    if reader_id:
        reader = Reader.objects.filter(library_id=reader_id).first()
        if reader:
            issued_books = IssueBook.objects.filter(
                reader=reader,
                is_returned=False
            )

    if book_q:
        books = Book.objects.filter(
            Q(title__icontains=book_q) |
            Q(ubno__icontains=book_q),
            available_copies__gt=0
        )

    if request.method == 'POST':
        reader = get_object_or_404(Reader, library_id=request.POST.get('reader_id'))
        book = get_object_or_404(Book, id=request.POST.get('book_id'))

        if IssueBook.objects.filter(reader=reader, is_returned=False).count() >= reader.issue_limit:
            messages.error(request, "Issue limit reached")
            return redirect(f"{request.path}?reader_id={reader.library_id}")

        if IssueBook.objects.filter(reader=reader, book=book, is_returned=False).exists():
            messages.error(request, "Book already issued to this reader")
            return redirect(f"{request.path}?reader_id={reader.library_id}")

        if book.available_copies <= 0:
            messages.error(request, "Book not available")
            return redirect(f"{request.path}?reader_id={reader.library_id}")

        with transaction.atomic():
            IssueBook.objects.create(reader=reader, book=book)
            book.available_copies -= 1
            book.save()

        messages.success(request, "Book issued successfully")
        return redirect(f"{request.path}?reader_id={reader.library_id}")

    return render(request, 'issue_book.html', {
        'reader_q': reader_q,
        'book_q': book_q,
        'readers': readers,
        'books': books,
        'selected_reader': reader,
        'issued_books': issued_books
    })


# ---------------- CHANGE MEMBERSHIP ----------------
@login_required(login_url='/login/')
@never_cache
def change_membership(request, reader_id):
    if not request.user.is_staff:
        return redirect('login')

    reader = get_object_or_404(Reader, library_id=reader_id)

    if request.method == 'POST':
        reader.membership = request.POST.get('membership')
        reader.save()
        messages.success(request, "Membership updated successfully")
        return redirect('view_reader')

    return render(request, 'change_membership.html', {'reader': reader})


# ---------------- AJAX READER SEARCH ----------------
@login_required(login_url='/login/')
@never_cache
def reader_search(request):
    q = request.GET.get('q', '')
    readers = Reader.objects.filter(
        Q(name__icontains=q) |
        Q(phone__icontains=q) |
        Q(email__icontains=q)
    )[:10]

    return JsonResponse([
        {'id': str(r.library_id), 'name': r.name, 'phone': r.phone}
        for r in readers
    ], safe=False)


# ---------------- RETURN BOOK ----------------
@login_required(login_url='/login/')
@never_cache
def return_book(request):
    if not request.user.is_staff:
        return redirect('login')

    reader = None
    issued_books = []
    reader_key = request.GET.get('reader_key')

    if reader_key:
        try:
            UUID(reader_key)
            reader = Reader.objects.filter(library_id=reader_key).first()
        except ValueError:
            reader = Reader.objects.filter(phone=reader_key).first()

        if reader:
            issued_books = IssueBook.objects.filter(
                reader=reader,
                is_returned=False
            )
        else:
            messages.error(request, "Reader not found")

    if request.method == 'POST':
        issue = get_object_or_404(
            IssueBook,
            id=request.POST.get('issue_id'),
            is_returned=False
        )

        with transaction.atomic():
            issue.is_returned = True
            issue.return_date = timezone.now().date()
            issue.save()

            book = issue.book
            book.available_copies += 1
            book.save()

        messages.success(request, "Book returned successfully")
        return redirect('return_book')

    return render(request, 'return_book.html', {
        'reader': reader,
        'issued_books': issued_books,
        'reader_key': reader_key
    })

#----------------- READER HISTORY ----------------
@login_required(login_url='/login/')
@never_cache
def reader_history(request, reader_id):
    if not request.user.is_staff:
        return redirect('login')

    reader = get_object_or_404(Reader, library_id=reader_id)

    issues = IssueBook.objects.filter(
        reader=reader
    ).select_related('book').order_by('-issue_date')

    return render(request, 'reader_history.html', {
        'reader': reader,
        'issues': issues
    })

#----------------- ACTIVE READERS ----------------
@login_required(login_url='/login/')
@never_cache
def active_readers(request):
    if not request.user.is_staff:
        return redirect('login')

    readers = Reader.objects.filter(
        issued_books__is_returned=False
    ).distinct()

    # 🔥 add active_count for each reader
    for r in readers:
        r.active_count = r.issued_books.filter(
            is_returned=False
        ).count()

    return render(request, 'active_readers.html', {
        'readers': readers
    })
