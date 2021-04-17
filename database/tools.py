from functools import wraps
from typing import List

from sqlalchemy import Column, String, Integer, Boolean, BigInteger, null, Table
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

from helper.discord_helper import generate_embed
from helper.utils import convert_to_bool

Base = declarative_base()

def none_as_null(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """
        Replace None as null()
        """
        func(self, *args, **kwargs)
        for k, v in self.__dict__.items():
            if v is None:
                setattr(self, k, null())

    return wrapper

def get_table_schema_name(table: DeclarativeMeta) -> str:
    return getattr(table, "__name__", None)


def get_table_columns(table: Table) -> List[Column]:
    return table.columns._all_columns


def get_table_column_names(table: Table) -> List[str]:
    columns = get_table_columns(table=table)
    return [column.name for column in columns]


def table_schema_to_name_type_pairs(table: Table):
    columns = get_table_columns(table=table)
    pairs = {}
    ignore_columns = getattr(table, "_ignore", [])
    for column in columns:
        if column not in ignore_columns:
            pairs[column.name] = sql_type_to_human_type_string(column.type)
    return pairs


def table_schema_to_discord_embed(table_name: str, table: Table):
    name_type_pairs = table_schema_to_name_type_pairs(table=table)
    return generate_embed(title=table_name, **name_type_pairs)


def table_values_to_discord_embeds(database, table_name: str, table: Table, get_all: bool = False):
    column_names = [column.name for column in table.columns]
    embeds = []
    if get_all:
        entries = database.get_all_entries(table_schema=table)
    else:
        entries = [database.get_first_entry(table_schema=table)]
    if not entries:
        embeds.append(f"There are no {table_name} entries currently.")
        return embeds
    for entry in entries:
        kwargs = {}
        for column_name in column_names:
            kwargs[column_name] = getattr(entry, column_name, None)
        embed = generate_embed(title=table_name, **kwargs)
        embeds.append(embed)
    return embeds


def sql_type_to_human_type_string(sql_type) -> str:
    if not hasattr(sql_type, "python_type"):
        return ""

    python_type = sql_type.python_type
    if python_type == str:
        return "String"
    elif python_type in [int, float]:
        return "Number"
    elif python_type == bool:
        return "True/False"
    return ""


def human_type_to_python_type(human_type: str):
    try:
        return float(human_type)  # is it a float?
    except:
        try:
            return int(human_type)  # is it an int?
        except:
            bool_value = convert_to_bool(bool_string=human_type)
            if bool_value is not None:  # is is a boolean?
                return bool_value
            else:
                return human_type  # it's a string