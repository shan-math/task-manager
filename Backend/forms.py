from flask_wtf import FlaskForm
from wtforms import (
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError

from utils import parse_date_input


def _optional_dd_mm_yyyy(form, field):
    if field.data and not parse_date_input(field.data):
        raise ValidationError("Use date format dd-mm-yyyy (e.g. 18-05-2026).")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=100)])
    password = PasswordField("Password", validators=[DataRequired()])


class SignupForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )


_DATE_PICKER_KW = {
    "class": "input date-picker",
    "placeholder": "dd-mm-yyyy",
    "autocomplete": "off",
}


class TaskForm(FlaskForm):
    task = StringField("Title", validators=[DataRequired(), Length(max=500)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=5000)])
    priority = SelectField(
        "Priority",
        choices=[("High", "High"), ("Medium", "Medium"), ("Low", "Low")],
        validators=[DataRequired()],
    )
    status = SelectField(
        "Status",
        choices=[
            ("Incomplete", "Incomplete"),
            ("In Progress", "In Progress"),
            ("Complete", "Complete"),
        ],
        validators=[DataRequired()],
    )
    user_id = SelectField("Assign to", coerce=int, validators=[DataRequired()])
    category_id = SelectField("Category", coerce=int, validators=[Optional()])
    due_date = StringField(
        "Due date (dd-mm-yyyy)",
        validators=[Optional(), _optional_dd_mm_yyyy],
        render_kw=_DATE_PICKER_KW,
    )
    tags = SelectMultipleField("Tags", coerce=int, validators=[Optional()])


class CommentForm(FlaskForm):
    body = TextAreaField("Comment", validators=[DataRequired(), Length(max=2000)])


class UserAdminForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    role = SelectField(
        "Role",
        choices=[("user", "User"), ("manager", "Manager"), ("admin", "Admin")],
        validators=[DataRequired()],
    )
    team_id = SelectField("Team", coerce=int, validators=[Optional()])
    password = PasswordField("Password", validators=[Optional(), Length(min=8)])


class BulkActionForm(FlaskForm):
    action = SelectField(
        "Action",
        choices=[
            ("delete", "Delete"),
            ("status_incomplete", "Set Incomplete"),
            ("status_progress", "Set In Progress"),
            ("status_complete", "Set Complete"),
        ],
        validators=[DataRequired()],
    )


class CategoryForm(FlaskForm):
    name = StringField("Category name", validators=[DataRequired(), Length(max=100)])
