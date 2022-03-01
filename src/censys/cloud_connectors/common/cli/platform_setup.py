"""Base for all platform-specific setup cli commands."""
from logging import Logger
from typing import Any, Callable, Union, get_origin

from pydantic.fields import ModelField
from pydantic.utils import lenient_issubclass
from PyInquirer import prompt

from censys.cloud_connectors.common.enums import PlatformEnum
from censys.cloud_connectors.common.logger import get_logger
from censys.cloud_connectors.common.settings import PlatformSpecificSettings, Settings


def snake_case_to_english(snake_case: str) -> str:
    """Convert a snake case string to an English sentence.

    Args:
        snake_case (str): The snake case string.

    Returns:
        str: The English sentence.
    """
    return " ".join(word.capitalize() for word in snake_case.split("_"))


def generate_validation(field: ModelField) -> Callable:
    """Generate a validation function for a field.

    Args:
        field (ModelField): The field to generate the validation for.

    Returns:
        Callable: The validation function.
    """

    def validate(value: Any) -> Union[bool, str]:
        """Validate the value.

        Args:
            value (Any): The value to validate.

        Returns:
            Union[bool, str]: True or the error message.
        """
        _, error = field.validate(value, {}, loc=field.name)
        if not error:
            return True
        while isinstance(error, list):
            # Sometimes the error is embedded in a nested list
            error = error[0]
        return str(error.exc)  # type: ignore

    return validate


def prompt_for_list(field: ModelField) -> list[str]:
    """Prompt for a list of values.

    Args:
        field (ModelField): The field to prompt for.

    Returns:
        List[str]: The list of values.

    Raises:
        KeyboardInterrupt: If the user cancels the prompt.
    """
    questions = [
        {
            "type": "input",
            "name": field.name,
            "message": f"Enter a {snake_case_to_english(field.name)}",
            "validate": generate_validation(field),
        },
        {
            "type": "confirm",
            "name": "add_another",
            "message": "Add another",
        },
    ]
    answers = prompt(questions)
    if not answers:  # pragma: no cover
        raise KeyboardInterrupt
    values = [answers[field.name]]
    while answers.get("add_another", False):
        answers = prompt(questions)
        if not answers:
            # break instead of raise KeyboardInterrupt
            break
        values.append(str(answers[field.name]).strip())
    return values


class PlatformSetupCli:
    """Base for all platform-specific setup cli commands."""

    platform: PlatformEnum
    platform_specific_settings_class: type[PlatformSpecificSettings]
    settings: Settings
    logger: Logger

    def __init__(self, settings: Settings):
        """Initialize the platform setup cli command.

        Args:
            settings (Settings): The settings to use.
        """
        self.settings = settings
        self.logger = get_logger(
            log_name=f"{self.platform}_setup", level=settings.logging_level
        )

    def setup(self) -> None:
        """Setup the platform."""
        platform_settings = self.prompt_for_settings()
        self.settings.platforms[self.platform].append(platform_settings)

    def prompt_for_settings(self) -> PlatformSpecificSettings:
        """Prompt for settings.

        Returns:
            PlatformSpecificSettings: The settings.

        Raises:
            ValueError: If the settings are invalid.
        """
        excluded_fields: list[str] = ["platform"]
        settings_fields: dict[
            str, ModelField
        ] = self.platform_specific_settings_class.__fields__
        questions = []
        answers = {}
        type_cast_map: dict[str, type] = {}
        for field in settings_fields.values():
            if field.name in excluded_fields:
                continue
            question = {
                "name": field.name,
                "message": f"{snake_case_to_english(field.name)}:",
                "validate": generate_validation(field),
            }
            field_type = field.type_
            if lenient_issubclass(field.outer_type_, list) or lenient_issubclass(
                get_origin(field.outer_type_), list
            ):
                answers[field.name] = prompt_for_list(field)
                continue
            elif lenient_issubclass(field_type, bool):
                question["type"] = "confirm"
            elif lenient_issubclass(field_type, (str, int, float)):
                question["type"] = "input"
                question["message"] = "Enter a " + question["message"]  # type: ignore

                # TODO: Is this something we want?
                if "secret" in field.name.lower():
                    question["type"] = "password"

                # Cast to type if float or int
                if lenient_issubclass(field_type, float):
                    type_cast_map[field.name] = float
                elif lenient_issubclass(field_type, int):
                    type_cast_map[field.name] = int
            else:  # pragma: no cover
                self.logger.debug(f"Unsupported field type: {field_type}")
                raise ValueError(f"Unsupported type for field {field.name}.")

            questions.append(question)
        answers.update(prompt(questions))
        if not answers:  # pragma: no cover
            raise ValueError("No answers provided.")
        if type_cast_map:
            for key, type_ in type_cast_map.items():
                answers[key] = type_(answers[key])
        return self.platform_specific_settings_class(**answers)
