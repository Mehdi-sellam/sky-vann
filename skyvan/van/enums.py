class VanStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    SOLD = "sold"
    BROKEN = "broken"
    CHOICES = [
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
        (SOLD, "Sold"),
        (BROKEN, "Broken"),
    ]
