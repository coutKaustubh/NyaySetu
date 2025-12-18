from django.db import models
from django.contrib.auth.models import User


class Residential(models.Model):
    house_number = models.CharField(max_length=50)
    landmark = models.CharField(max_length=150, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.house_number}, {self.landmark}, {self.city}, {self.state} - {self.pincode}"


class IncidentLocation(models.Model):
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    location = models.CharField(max_length=150)  # e.g. "Market Area", "Park"
    landmark = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"{self.location}, {self.city}, {self.state}"


class Complaint(models.Model):

    class PrivacyChoices(models.TextChoices):
        LAWYERS_ONLY = "LAWYERS_ONLY", "Visible to Lawyers Only"
        PUBLIC_WITH_IDENTITY = "PUBLIC_WITH_IDENTITY", "Show Public with Identity"
        PUBLIC_ANONYMOUS = "PUBLIC_ANONYMOUS", "Show Public without Identity"
 
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaints")
    full_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    govt_id = models.CharField(max_length=50)  # e.g. Aadhaar, PAN
    dob = models.DateField()

    title = models.CharField(max_length=200)
    crime_description = models.TextField()
    incident_datetime = models.DateTimeField()

    residential_address = models.ForeignKey(Residential, on_delete=models.SET_NULL, null=True, related_name="complaints")
    incident_location = models.ForeignKey(IncidentLocation, on_delete=models.SET_NULL, null=True, related_name="incidents")

    photo = models.ImageField(upload_to="complaint_photos/", blank=True, null=True)
    file_of_complaint = models.FileField(upload_to="complaint_files/", blank=True, null=True)

    witness_name = models.CharField(max_length=100, blank=True, null=True)
    witness_contact = models.CharField(max_length=15, blank=True, null=True)

    privacy_option = models.CharField(
        max_length=30,
        choices=PrivacyChoices.choices,
        default=PrivacyChoices.LAWYERS_ONLY
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Complaint by {self.full_name} - {self.title}"
