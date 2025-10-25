from flask_wtf import FlaskForm
from wtforms import SelectField, FieldList, BooleanField, SubmitField


class SettingsForm(FlaskForm):
    per_page = SelectField(
        "Кол-во объектов на странице",
        choices=[
            ("8", "8"),
            ("16", "16"),
            ("24", "24"),
            ("32", "32"),
            ("0", "Все"),
        ],
        default="8",
    )
    pic = FieldList(
        SelectField(
            "Выбор картинки",
            choices=[
                ("250.jpg", "250.jpg"),
                ("500.webp", "500.webp"),
                ("1080.png", "1080.png"),
            ],
        ),
        min_entries=1,
    )
    html = BooleanField("html")
    css = BooleanField("css")
    submit = SubmitField("Сохранить")
