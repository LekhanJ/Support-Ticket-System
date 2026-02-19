from rest_framework import serializers
from .models import Ticket

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "category",
            "priority",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_category(self, value):
        valid = [c.value for c in Ticket.Category]
        if value not in valid:
            raise serializers.ValidationError(
                f"Invalid category. Must be one of: {', '.join(valid)}"
            )
        return value

    def validate_priority(self, value):
        valid = [p.value for p in Ticket.Priority]
        if value not in valid:
            raise serializers.ValidationError(
                f"Invalid priority. Must be one of: {', '.join(valid)}"
            )
        return value

    def validate_status(self, value):
        valid = [s.value for s in Ticket.Status]
        if value not in valid:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid)}"
            )
        return value


class ClassifyRequestSerializer(serializers.Serializer):
    description = serializers.CharField(min_length=10)


class ClassifyResponseSerializer(serializers.Serializer):
    suggested_category = serializers.ChoiceField(choices=Ticket.Category.choices)
    suggested_priority = serializers.ChoiceField(choices=Ticket.Priority.choices)
