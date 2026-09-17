from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Declarative Base for all KISANQUEUE V2 SQLAlchemy models.

    Provides standard table naming conventions and shared model metadata.
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Derives default snake_case table names from model class names."""
        # Split on uppercase letters to convert PascalCase to snake_case
        name = cls.__name__
        return "".join(
            ["_" + c.lower() if c.isupper() and i > 0 else c.lower() for i, c in enumerate(name)]
        )
