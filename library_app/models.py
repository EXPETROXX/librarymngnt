from django.db import models
import uuid

# ---------------- CATEGORY ----------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'category'

    def __str__(self):
        return self.name


# ---------------- BOOK ----------------
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    ubno = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='books'
    )
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'book'

    def save(self, *args, **kwargs):
        # 🔒 Ensure valid available copies
        if self.available_copies > self.total_copies:
            self.available_copies = self.total_copies
        if self.available_copies < 0:
            self.available_copies = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# ---------------- READER ----------------
class Reader(models.Model):

    MEMBERSHIP_CHOICES = [
        ('BASIC', 'Basic'),
        ('PREMIUM', 'Premium'),
        ('VIP', 'VIP'),
    ]

    library_id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True,
        editable=False
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=13)
    email = models.EmailField(max_length=100)
    address = models.CharField(max_length=150)

    membership = models.CharField(
        max_length=10,
        choices=MEMBERSHIP_CHOICES,
        default='BASIC'
    )

    issue_limit = models.PositiveIntegerField(default=3)

    class Meta:
        db_table = 'reader'

    def save(self, *args, **kwargs):
        # 🔒 Auto set issue limit based on membership
        if self.membership == 'BASIC':
            self.issue_limit = 3
        elif self.membership == 'PREMIUM':
            self.issue_limit = 5
        elif self.membership == 'VIP':
            self.issue_limit = 10
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ---------------- ISSUE BOOK ----------------
class IssueBook(models.Model):
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='issues'
    )
    reader = models.ForeignKey(
        Reader,
        on_delete=models.CASCADE,
        related_name='issued_books'
    )
    issue_date = models.DateField(auto_now_add=True)
    return_date = models.DateField(null=True, blank=True)
    is_returned = models.BooleanField(default=False)

    class Meta:
        db_table = 'issueBook'
        ordering = ['-issue_date']
        constraints = [
            # 🚫 Prevent issuing same book twice without return
            models.UniqueConstraint(
                fields=['book', 'reader', 'is_returned'],
                name='unique_active_issue'
            )
        ]

    def __str__(self):
        return f"{self.book.title} → {self.reader.name}"
