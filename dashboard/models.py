from django.db import models


class ProductivityDashboard(models.Model):
    """Picker Zone Plan — productivity block: main title, black banner, then cards."""

    module_number = models.CharField(
        max_length=16,
        default="01",
        verbose_name="Module number",
        help_text='Large number on the left (e.g. 01).',
    )
    dashboard_title = models.CharField(
        max_length=255,
        default="Productivity Dashboard",
        verbose_name="Dashboard title",
        help_text='Main headline after “MODULE” (e.g. Productivity Dashboard).',
    )
    intro_text = models.TextField(
        blank=True,
        verbose_name="Intro text (optional)",
        help_text="Optional paragraph under the main title and above the black banner.",
    )
    banner_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Banner title",
        help_text='Headline inside the black bar (e.g. Overtime Cap Rule).',
    )
    banner_text = models.TextField(
        blank=True,
        verbose_name="Banner text",
        help_text="Supporting text under the banner title (white text on black bar).",
    )
    banner_value = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Banner value",
        help_text="Right side of the bar, large accent (e.g. 150 hrs).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If several exist, the active one with the latest update is shown on the site.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "[Tab 1 — Zone plan] Productivity dashboard"
        verbose_name_plural = "[Tab 1 — Zone plan] Productivity dashboards"

    def __str__(self):
        return f"{self.module_number} — {self.dashboard_title}"


class ProductivityDashboardCard(models.Model):
    """One card: icon + title + body (like the wireframe cards)."""

    class IconKind(models.TextChoices):
        RED_OT = "red_ot", "Red arrow + OT"
        GREEN_OUT = "green_out", "Green arrow + OUT"
        BELL = "bell", "Bell"
        STOP = "stop", "Stop / cap bar"
        IMAGE = "image", "Uploaded image"

    dashboard = models.ForeignKey(
        ProductivityDashboard,
        on_delete=models.CASCADE,
        related_name="cards",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    icon_kind = models.CharField(
        max_length=16,
        choices=IconKind.choices,
        default=IconKind.BELL,
        verbose_name="Icon",
    )
    icon_image = models.ImageField(
        upload_to="productivity/card_icons/",
        blank=True,
        null=True,
        verbose_name="Custom icon image",
        help_text="Only when icon is “Uploaded image”.",
    )
    card_title = models.CharField(
        max_length=255,
        verbose_name="Card title",
        help_text="Small caps line under the icon (e.g. Overtime reduction).",
    )
    card_text = models.TextField(
        verbose_name="Card text",
        help_text="Body under the card title.",
    )

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "[Tab 1 — Zone plan] Productivity dashboard card"
        verbose_name_plural = "[Tab 1 — Zone plan] Productivity dashboard cards"

    def __str__(self):
        return self.card_title


class PickingMethodProgram(models.Model):
    """
    Phase-style block (e.g. PHASE 02 — Picking method 3-week test): header, week phases, summary strip.
    """

    module_number = models.CharField(
        max_length=16,
        default="02",
        verbose_name="Phase number",
        help_text="Large number on the left (e.g. 02).",
    )
    module_keyword = models.CharField(
        max_length=32,
        default="PHASE",
        verbose_name="Keyword",
        help_text="Small caps word after the number (e.g. PHASE).",
    )
    section_title = models.CharField(
        max_length=255,
        default="PICKING METHOD – 3-WEEK TEST",
        verbose_name="Section title",
        help_text="Bold headline after the keyword.",
    )
    intro_text = models.TextField(
        blank=True,
        verbose_name="Intro paragraph",
        help_text="Text under the header (e.g. three zone structures…).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If several exist, the active one with the latest update is shown on the site.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "[Tab 1 — Zone plan] Picking method program"
        verbose_name_plural = "[Tab 1 — Zone plan] Picking method programs"

    def __str__(self):
        return f"{self.module_number} {self.module_keyword} {self.section_title}"


class PickingMethodPhase(models.Model):
    """One week row: label, accent color, title, test badge, description, tags."""

    class Theme(models.TextChoices):
        RED = "red", "Red"
        ORANGE = "orange", "Orange"
        AMBER = "amber", "Amber"
        YELLOW = "yellow", "Yellow"
        LIME = "lime", "Lime"
        GREEN = "green", "Green"
        EMERALD = "emerald", "Emerald"
        TEAL = "teal", "Teal"
        CYAN = "cyan", "Cyan"
        SKY = "sky", "Sky"
        BLUE = "blue", "Blue"
        INDIGO = "indigo", "Indigo"
        VIOLET = "violet", "Violet"
        PURPLE = "purple", "Purple"
        FUCHSIA = "fuchsia", "Fuchsia"
        PINK = "pink", "Pink"
        ROSE = "rose", "Rose"
        SLATE = "slate", "Slate"
        STONE = "stone", "Stone"
        ZINC = "zinc", "Zinc"
        NEUTRAL = "neutral", "Neutral gray"

    program = models.ForeignKey(
        PickingMethodProgram,
        on_delete=models.CASCADE,
        related_name="phases",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    week_label = models.CharField(
        max_length=64,
        verbose_name="Week label",
        help_text="e.g. WEEK 1",
    )
    theme = models.CharField(
        max_length=24,
        choices=Theme.choices,
        default=Theme.RED,
        verbose_name="Accent color",
        help_text="Left border and dot color — pick a different color for each extra week.",
    )
    main_title = models.CharField(
        max_length=255,
        verbose_name="Main title",
        help_text="e.g. BY ROOM",
    )
    test_badge = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Test badge",
        help_text="e.g. TEST A",
    )
    description = models.TextField(
        verbose_name="Description",
        help_text="Paragraph for this week.",
    )

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "[Tab 1 — Zone plan] Picking method phase (week)"
        verbose_name_plural = "[Tab 1 — Zone plan] Picking method phases"

    def __str__(self):
        return f"{self.week_label} — {self.main_title}"


class PickingMethodPhaseTag(models.Model):
    """Tag pill under a phase (e.g. ROOM 1, CATEGORY A)."""

    phase = models.ForeignKey(
        PickingMethodPhase,
        on_delete=models.CASCADE,
        related_name="tags",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    label = models.CharField(max_length=128)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "[Tab 1 — Zone plan] Phase tag"
        verbose_name_plural = "[Tab 1 — Zone plan] Phase tags"

    def __str__(self):
        return self.label


class PickingMethodSummaryCard(models.Model):
    """Bottom strip card: large value + label (e.g. 3 / METHODS TESTED)."""

    program = models.ForeignKey(
        PickingMethodProgram,
        on_delete=models.CASCADE,
        related_name="summary_cards",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    display_value = models.CharField(
        max_length=32,
        verbose_name="Display value",
        help_text='Large text or symbol (e.g. 3, 1W, →1, ∞).',
    )
    label = models.CharField(
        max_length=128,
        verbose_name="Label",
        help_text="e.g. METHODS TESTED",
    )

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "[Tab 1 — Zone plan] Picking method summary card"
        verbose_name_plural = "[Tab 1 — Zone plan] Picking method summary cards"

    def __str__(self):
        return f"{self.display_value} — {self.label}"


class BarrierProgram(models.Model):
    """Module 03 style: Barriers — Identified challenges."""

    module_number = models.CharField(
        max_length=16,
        default="03",
        verbose_name="Module number",
        help_text="Large number on the left (e.g. 03).",
    )
    module_keyword = models.CharField(
        max_length=32,
        default="BARRIERS",
        verbose_name="Keyword",
        help_text="Small label (e.g. BARRIERS).",
    )
    section_title = models.CharField(
        max_length=255,
        default="IDENTIFIED CHALLENGES",
        verbose_name="Section title",
        help_text="Main headline after the keyword.",
    )
    intro_text = models.TextField(
        blank=True,
        verbose_name="Intro (optional)",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If several exist, the active one with the latest update is shown on the site.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "[Tab 1 — Zone plan] Barrier program"
        verbose_name_plural = "[Tab 1 — Zone plan] Barrier programs"

    def __str__(self):
        return f"{self.module_number} {self.module_keyword} {self.section_title}"


class BarrierChallenge(models.Model):
    """One challenge card: title, problem, optional mitigation, impact badge."""

    class Impact(models.TextChoices):
        HIGH = "high", "High impact"
        MEDIUM = "medium", "Medium impact"
        LOW = "low", "Low impact"

    program = models.ForeignKey(
        BarrierProgram,
        on_delete=models.CASCADE,
        related_name="challenges",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    title = models.CharField(
        max_length=255,
        verbose_name="Challenge title",
        help_text='Shown with a warning icon (e.g. "Truck Arrival — Unknown Timing"). You may include ⚠ in the text.',
    )
    problem_description = models.TextField(
        verbose_name="Problem details",
        help_text="Describe the issue.",
    )
    mitigation_text = models.TextField(
        blank=True,
        verbose_name="Mitigation (solution)",
        help_text="How you plan to fix it. Leave empty to show the placeholder text instead.",
    )
    mitigation_placeholder = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Placeholder when no mitigation",
        help_text="If mitigation is empty, this shows (default: generic “coming soon” message if you leave this blank too).",
    )
    impact = models.CharField(
        max_length=16,
        choices=Impact.choices,
        default=Impact.HIGH,
        verbose_name="Impact level",
    )

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "[Tab 1 — Zone plan] Barrier challenge"
        verbose_name_plural = "[Tab 1 — Zone plan] Barrier challenges"

    def __str__(self):
        return self.title


class RolloutProgram(models.Model):
    """Module 04 style: Rollout — Implementation plan (horizontal cards)."""

    module_number = models.CharField(
        max_length=16,
        default="04",
        verbose_name="Module number",
        help_text="Large number on the left (e.g. 04).",
    )
    module_keyword = models.CharField(
        max_length=32,
        default="ROLLOUT",
        verbose_name="Keyword",
        help_text="Small label (e.g. ROLLOUT).",
    )
    section_title = models.CharField(
        max_length=255,
        default="IMPLEMENTATION PLAN",
        verbose_name="Section title",
        help_text="Main headline after the keyword.",
    )
    intro_text = models.TextField(
        blank=True,
        verbose_name="Intro paragraph",
        help_text="Text under the main title (e.g. conditional rollout explanation).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If several exist, the active one with the latest update is shown on the site.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "[Tab 1 — Zone plan] Rollout program"
        verbose_name_plural = "[Tab 1 — Zone plan] Rollout programs"

    def __str__(self):
        return f"{self.module_number} {self.module_keyword} {self.section_title}"


class RolloutPlanCard(models.Model):
    """One implementation card: top accent, icon, title, description."""

    class AccentTheme(models.TextChoices):
        RED = "red", "Red"
        ORANGE = "orange", "Orange"
        AMBER = "amber", "Amber"
        YELLOW = "yellow", "Yellow"
        LIME = "lime", "Lime"
        GREEN = "green", "Green"
        EMERALD = "emerald", "Emerald"
        TEAL = "teal", "Teal"
        CYAN = "cyan", "Cyan"
        SKY = "sky", "Sky"
        BLUE = "blue", "Blue"
        INDIGO = "indigo", "Indigo"
        VIOLET = "violet", "Violet"
        PURPLE = "purple", "Purple"
        FUCHSIA = "fuchsia", "Fuchsia"
        PINK = "pink", "Pink"
        ROSE = "rose", "Rose"
        SLATE = "slate", "Slate"
        STONE = "stone", "Stone"
        ZINC = "zinc", "Zinc"
        NEUTRAL = "neutral", "Neutral gray"

    class IconKind(models.TextChoices):
        GRID_BAYS = "grid_bays", "Numbered grid (1–4)"
        MONITOR = "monitor", "Screen / monitor"
        SMARTPHONE = "smartphone", "Smartphone"
        WAREHOUSE = "warehouse", "Warehouse"
        TRUCK = "truck", "Truck"
        CHECKLIST = "checklist", "Checklist"
        CUSTOM = "custom", "Uploaded image"

    program = models.ForeignKey(
        RolloutProgram,
        on_delete=models.CASCADE,
        related_name="plan_cards",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    accent_theme = models.CharField(
        max_length=24,
        choices=AccentTheme.choices,
        default=AccentTheme.BLUE,
        verbose_name="Accent color",
        help_text="Top border color on the card.",
    )
    icon_kind = models.CharField(
        max_length=24,
        choices=IconKind.choices,
        default=IconKind.GRID_BAYS,
        verbose_name="Icon",
    )
    icon_image = models.ImageField(
        upload_to="rollout/card_icons/",
        blank=True,
        null=True,
        verbose_name="Custom icon",
        help_text="When icon is “Uploaded image”.",
    )
    card_title = models.CharField(
        max_length=255,
        verbose_name="Card title",
    )
    card_description = models.TextField(
        verbose_name="Card description",
    )

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "[Tab 1 — Zone plan] Rollout plan card"
        verbose_name_plural = "[Tab 1 — Zone plan] Rollout plan cards"

    def __str__(self):
        return self.card_title


class ProcessImprovementProgram(models.Model):
    """Module 05 style: Enhancements — Process improvements (stacked full-width cards)."""

    module_number = models.CharField(
        max_length=16,
        default="05",
        verbose_name="Module number",
        help_text="Large number on the left (e.g. 05).",
    )
    module_keyword = models.CharField(
        max_length=32,
        default="ENHANCEMENTS",
        verbose_name="Keyword",
        help_text="Small uppercase line (e.g. ENHANCEMENTS).",
    )
    section_title = models.CharField(
        max_length=255,
        default="PROCESS IMPROVEMENTS",
        verbose_name="Section title",
        help_text="Main headline after the keyword.",
    )
    intro_text = models.TextField(
        blank=True,
        verbose_name="Intro (optional)",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If several exist, the active one with the latest update is shown on the site.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "[Tab 1 — Zone plan] Process improvement program"
        verbose_name_plural = "[Tab 1 — Zone plan] Process improvement programs"

    def __str__(self):
        return f"{self.module_number} {self.module_keyword} {self.section_title}"


class ProcessImprovementItem(models.Model):
    """One full-width improvement block (dark or colored background)."""

    class Surface(models.TextChoices):
        DARK = "dark", "Dark (black)"
        BLUE = "blue", "Blue"
        INDIGO = "indigo", "Indigo"
        TEAL = "teal", "Teal"
        SLATE = "slate", "Slate"
        STONE = "stone", "Stone"
        EMERALD = "emerald", "Emerald"
        VIOLET = "violet", "Violet"
        ORANGE = "orange", "Orange"
        ROSE = "rose", "Rose"

    program = models.ForeignKey(
        ProcessImprovementProgram,
        on_delete=models.CASCADE,
        related_name="items",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    surface = models.CharField(
        max_length=16,
        choices=Surface.choices,
        default=Surface.DARK,
        verbose_name="Card background",
        help_text="Dark = black card like improvement 01; colored surfaces for emphasis.",
    )
    improvement_label = models.CharField(
        max_length=64,
        default="IMPROVEMENT 01",
        verbose_name="Improvement label",
        help_text='First part of the meta line (e.g. "IMPROVEMENT 01").',
    )
    category_label = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Category tag",
        help_text='Second part after the middle dot (e.g. "SMALL ACCOUNTS"). Leave empty to hide the dot.',
    )
    card_title = models.CharField(
        max_length=255,
        verbose_name="Main title",
        help_text="Bold white headline on the card.",
    )
    body_text = models.TextField(
        verbose_name="Body text",
        help_text="Supporting paragraph on the card.",
    )

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "[Tab 1 — Zone plan] Process improvement item"
        verbose_name_plural = "[Tab 1 — Zone plan] Process improvement items"

    def __str__(self):
        return self.card_title


class PickerPerformanceProgram(models.Model):
    """
    Tab 2 — Picker Performance: line-level SAP rows (Admin or Excel import), KPIs derived in the view.
    Import reads the Excel uploaded in Admin (Business = company name).
    """

    title = models.CharField(
        max_length=255,
        default="Picker performance",
        verbose_name="Section title",
    )
    subtitle = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Subtitle",
        help_text="e.g. Reach truck · target lines per shift.",
    )
    target_lines = models.PositiveSmallIntegerField(
        default=200,
        verbose_name="Target lines (green shift)",
        help_text="Shifts at or above this count as green for KPIs and legend.",
    )
    period_label = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Period label",
        help_text='Shown in the header (e.g. "Oct 1–30, 2025").',
    )
    excel_sheet_name = models.CharField(
        max_length=64,
        default="Data",
        verbose_name="Excel sheet name",
        help_text="Sheet to read on Admin import (use Data for Picking .xlsx). If missing, import tries Data then the first sheet.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If several exist, the active one with the latest update is used on the home page.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "[Tab 2 — Picker performance] Program"
        verbose_name_plural = "[Tab 2 — Picker performance] Programs"

    def __str__(self):
        return self.title


class PickerShiftRecord(models.Model):
    """One picked line from SAP (raw input for aggregations)."""

    class ShiftBand(models.TextChoices):
        S1 = "S1", "Shift 1 (06:00–15:00)"
        S2 = "S2", "Shift 2 (15:00–00:00)"
        S3 = "S3", "Shift 3 (00:00–06:00)"
        MORNING = "MORNING", "Morning (legacy)"
        EVENING = "EVENING", "Evening / night (legacy)"
        OTHER = "OTHER", "Other / unknown"

    program = models.ForeignKey(
        PickerPerformanceProgram,
        on_delete=models.CASCADE,
        related_name="shifts",
    )
    work_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date",
        help_text="Confirmation date (required for trends and weekday KPIs).",
    )
    picker_name = models.CharField(max_length=128, verbose_name="Picker name")
    lines = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Lines",
        help_text="Always 1 per SAP row (one row = one line).",
    )
    is_pick = models.BooleanField(
        default=False,
        verbose_name="Is PICK",
        help_text='True when Source Storage Bin starts with "PICK".',
    )
    shift_band = models.CharField(
        max_length=16,
        choices=ShiftBand.choices,
        default=ShiftBand.OTHER,
        verbose_name="Shift",
        help_text="S1/S2/S3 from Confirmation time.",
    )
    pick_duration_min = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Pick duration (min)",
        help_text="(Confirmation − Creation) in minutes.",
    )
    delivery_number = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Delivery number",
    )
    picker_type = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Type",
        help_text='SAP column Type (e.g. "Operator").',
    )
    business = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="Business",
        help_text="Company name from the Excel Business column.",
        db_index=True,
    )

    class Meta:
        ordering = ("work_date", "picker_name", "id")
        verbose_name = "[Tab 2 — Picker performance] Line record"
        verbose_name_plural = "[Tab 2 — Picker performance] Line records"

    def __str__(self):
        d = self.work_date.isoformat() if self.work_date else "?"
        return f"{self.picker_name} · {d} · {self.lines}L"


class DashboardWorkbook(models.Model):
    """
    Excel workbook for the home page Daily Tracker (tab 4).
    Must include a sheet named "Daily Tracker" with Picker Name + dated columns.
    """

    title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Title (optional)",
        help_text="Optional label in Admin only.",
    )
    file = models.FileField(
        upload_to="dashboard_workbooks/%Y/%m/",
        verbose_name="Workbook (.xlsx / .xlsm)",
        help_text='Must include a sheet named "Daily Tracker" with a Picker Name row and date columns.',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Only one active record is used. When active, visitors see this data unless they upload another file in the same browser session (Zone Dispatch tab).",
    )
    parsed_snapshot = models.JSONField(
        null=True,
        blank=True,
        editable=False,
        verbose_name="Parsed Daily Tracker (auto)",
        help_text="Filled when the file is saved if the Daily Tracker sheet is valid.",
    )

    class Meta:
        ordering = ("-uploaded_at",)
        verbose_name = "[Tab 4 — Daily Tracker] Workbook upload"
        verbose_name_plural = "[Tab 4 — Daily Tracker] Workbook uploads"

    def __str__(self):
        if self.title:
            return self.title
        if self.file:
            return self.file.name.rsplit("/", 1)[-1]
        return "Workbook"
