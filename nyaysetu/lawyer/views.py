from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F, Q

from .models import LawyerProfile, City, SPECIALIZATIONS, ContactRequest
from complaints.models import Complaint
from django.db import IntegrityError


# Serializers
class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name"]


class LawyerProfileSerializer(serializers.ModelSerializer):
    # Represent the user as a read-only primary key (could be expanded later)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    # Nested read for cities and write using IDs
    service_cities = CitySerializer(many=True, read_only=True)
    service_city_ids = serializers.PrimaryKeyRelatedField(
        source="service_cities",
        queryset=City.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )

    # Computed win-rate percentage
    win_rate = serializers.SerializerMethodField()

    def get_win_rate(self, obj):
        try:
            return round((obj.won_cases / obj.total_cases) * 100, 2) if obj.total_cases else 0.0
        except ZeroDivisionError:
            return 0.0

    class Meta:
        model = LawyerProfile
        fields = [
            "id",
            "user",
            "specialization",
            "experience_years",
            "license_number",
            "bio",
            "contact_number",
            "address",
            "rating",
            "total_cases",
            "won_cases",
            "service_cities",
            "service_city_ids",
            "win_rate",
        ]

    def create(self, validated_data):
        # service_cities comes via source mapping when writing service_city_ids
        cities = validated_data.pop("service_cities", [])
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            raise serializers.ValidationError({"detail": "Authentication required to create a profile."})
        if hasattr(user, "lawyer_profile"):
            raise serializers.ValidationError({"detail": "Profile already exists for this user."})
        profile = LawyerProfile.objects.create(user=user, **validated_data)
        if cities:
            profile.service_cities.set(cities)
        return profile

    def update(self, instance, validated_data):
        cities = validated_data.pop("service_cities", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if cities is not None:
            instance.service_cities.set(cities)
        return instance

    def validate_service_city_ids(self, value):
        if value and len(value) > 4:
            raise serializers.ValidationError("You can select up to 4 cities.")
        return value

class ComplaintBriefSerializer(serializers.ModelSerializer):
    incident_city = serializers.CharField(source="incident_location.city", read_only=True)
    residential_city = serializers.CharField(source="residential_address.city", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "title",
            "created_at",
            "privacy_option",
            "incident_city",
            "residential_city",
        ]

class ContactRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactRequest
        fields = ["id", "user", "lawyer", "message", "status", "created_at"]
        read_only_fields = ["user", "status", "created_at"]


# ViewSets
class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.all().order_by("name")
    serializer_class = CitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class LawyerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = LawyerProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = (
            LawyerProfile.objects.select_related("user")
            .prefetch_related("service_cities")
            .all()
        )

        # Filtering via query params
        params = self.request.query_params
        specialization = params.get("specialization")
        city = params.get("city")  # accepts city id or name
        min_exp = params.get("min_experience")
        q = params.get("q")  # free-text search

        if specialization:
            qs = qs.filter(specialization=specialization)
        if city:
            if str(city).isdigit():
                qs = qs.filter(service_cities__id=int(city))
            else:
                qs = qs.filter(service_cities__name__iexact=city)
        if min_exp and str(min_exp).isdigit():
            qs = qs.filter(experience_years__gte=int(min_exp))
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(bio__icontains=q)
                | Q(license_number__icontains=q)
            )

        return qs.distinct()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated:
            raise serializers.ValidationError({"detail": "Authentication required."})
        if hasattr(user, "lawyer_profile"):
            raise serializers.ValidationError({"detail": "Profile already exists for this user."})
        serializer.save(user=user)

    @action(detail=False, methods=["get"], url_path="specializations")
    def list_specializations(self, request):
        data = [{"key": k, "label": v} for k, v in SPECIALIZATIONS]
        return Response(data)

    @action(detail=False, methods=["get"], url_path="top")
    def top_lawyers(self, request):
        qs = self.get_queryset().order_by("-rating", "-won_cases")[:10]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="add-city", permission_classes=[permissions.IsAuthenticated])
    def add_city(self, request, pk=None):
        city_id = request.data.get("city_id")
        if not city_id:
            return Response({"detail": "city_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        city = get_object_or_404(City, pk=city_id)
        profile = self.get_object()
        profile.service_cities.add(city)
        return Response({"status": "added", "city": CitySerializer(city).data})

    @action(detail=True, methods=["post"], url_path="remove-city", permission_classes=[permissions.IsAuthenticated])
    def remove_city(self, request, pk=None):
        city_id = request.data.get("city_id")
        if not city_id:
            return Response({"detail": "city_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        city = get_object_or_404(City, pk=city_id)
        profile = self.get_object()
        profile.service_cities.remove(city)
        return Response({"status": "removed", "city": CitySerializer(city).data})

    @action(detail=True, methods=["post"], url_path="increment-cases", permission_classes=[permissions.IsAuthenticated])
    def increment_cases(self, request, pk=None):
        won = request.data.get("won")
        won_flag = str(won).lower() in {"true", "1", "yes"}
        profile = self.get_object()
        profile.total_cases = F("total_cases") + 1
        if won_flag:
            profile.won_cases = F("won_cases") + 1
        profile.save(update_fields=["total_cases", "won_cases"])
        profile.refresh_from_db()
        return Response({"total_cases": profile.total_cases, "won_cases": profile.won_cases})

    @action(detail=False, methods=["get", "put", "patch"], url_path="me", permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        # Get or update the current user's lawyer profile
        try:
            instance = request.user.lawyer_profile
        except LawyerProfile.DoesNotExist:
            if request.method in ["PUT", "PATCH"]:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save(user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "GET":
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        partial = request.method == "PATCH"
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="contact", permission_classes=[permissions.IsAuthenticated])
    def contact(self, request, pk=None):
        lawyer = self.get_object()
        message = request.data.get("message", "")
        try:
            cr = ContactRequest.objects.create(user=request.user, lawyer=lawyer, message=message)
        except IntegrityError:
            return Response({"detail": "Request already sent."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ContactRequestSerializer(cr).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="cases", permission_classes=[permissions.IsAuthenticated])
    def cases(self, request):
        try:
            profile = request.user.lawyer_profile
        except LawyerProfile.DoesNotExist:
            return Response({"detail": "Lawyer profile required."}, status=status.HTTP_403_FORBIDDEN)
        names = list(profile.service_cities.values_list("name", flat=True))
        qs = Complaint.objects.filter(
            Q(incident_location__city__in=names) | Q(residential_address__city__in=names)
        ).order_by("-created_at")
        data = ComplaintBriefSerializer(qs, many=True).data
        return Response(data)

    @action(detail=False, methods=["get"], url_path="search-cases", permission_classes=[permissions.IsAuthenticated])
    def search_cases(self, request):
        cities_param = request.query_params.get("cities")
        names = []
        if cities_param:
            tokens = [t.strip() for t in cities_param.split(",") if t.strip()]
            id_tokens = [int(t) for t in tokens if t.isdigit()]
            name_tokens = [t for t in tokens if not t.isdigit()]
            if id_tokens:
                names.extend(list(City.objects.filter(id__in=id_tokens).values_list("name", flat=True)))
            if name_tokens:
                names.extend(name_tokens)
        if not names:
            return Response({"detail": "Provide cities by id or name."}, status=status.HTTP_400_BAD_REQUEST)
        qs = Complaint.objects.filter(
            Q(incident_location__city__in=names) | Q(residential_address__city__in=names)
        ).order_by("-created_at")
        return Response(ComplaintBriefSerializer(qs, many=True).data)
