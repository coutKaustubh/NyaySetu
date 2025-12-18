# lawyers/models.py
from django.db import models
from django.contrib.auth.models import User
SPECIALIZATIONS = [
    ('civil', 'Civil Law'),
    ('criminal', 'Criminal Law'),
    ('family', 'Family Law'),
    ('property', 'Property / Real Estate Law'),
    ('corporate', 'Corporate Law'),
    ('business', 'Commercial / Business Law'),
    ('contract', 'Contract Law'),
    ('banking', 'Banking & Finance Law'),
    ('competition', 'Competition Law'),
    ('insolvency', 'Insolvency / Bankruptcy Law'),
    ('administrative', 'Administrative Law'),
    ('constitutional', 'Constitutional Law'),
    ('human_rights', 'Human Rights / Public Interest Law'),
    ('environmental', 'Environmental Law'),
    ('international', 'International Law / Trade Law'),
    ('immigration', 'Immigration Law'),
    ('intellectual_property', 'Intellectual Property Rights (IPR)'),
    ('cyber', 'Cyber Law / Data Privacy'),
    ('technology', 'Technology / IT Law'),
    ('fintech', 'Fintech, Blockchain & Emerging Tech'),
    ('media_entertainment', 'Media & Entertainment Law'),
    ('labour_employment', 'Labour & Employment Law'),   
    ('tax', 'Taxation Law'),
    ('consumer_protection', 'Consumer Protection Law'),
    ('insurance', 'Insurance Law'),
    ('maritime', 'Maritime / Admiralty Law'),
    ('personal_injury', 'Personal Injury / Tort Law'),
    ('space_air', 'Space & Air Law'),
    ('defense_military', 'Military / Armed Forces / Defence Law'),
    ('other', 'Other'),
]


class City(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
 
class LawyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="lawyer_profile")
    specialization = models.CharField(max_length=50, choices=SPECIALIZATIONS, default='other')
    experience_years = models.PositiveIntegerField(default=0)
    license_number = models.CharField(max_length=100, unique=True)
    bio = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    rating = models.FloatField(default=0.0)
    total_cases = models.PositiveIntegerField(default=0)
    won_cases = models.PositiveBigIntegerField(default=0)
    service_cities = models.ManyToManyField(City, related_name="lawyers")

    def __str__(self):
        return f"Lawyer: {self.user.get_full_name()} ({self.specialization})"


class ContactRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lawyer_contact_requests")
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name="contact_requests")
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "lawyer"], name="unique_user_lawyer_contact_once")
        ]

    def __str__(self):
        return f"ContactRequest from {self.user_id} to lawyer {self.lawyer_id}"
