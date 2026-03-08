"""
Modelli Pydantic per la validazione degli input degli strumenti MCP.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class CercaStazioneInput(BaseModel):
    """Input per la ricerca di una stazione per nome."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    nome_stazione: str = Field(
        ...,
        description="Nome parziale o completo della stazione (es. 'Milano', 'Roma Termini', 'Napoli')",
        min_length=2,
        max_length=100,
    )

    @field_validator("nome_stazione")
    @classmethod
    def validate_nome(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Il nome stazione non può essere vuoto.")
        return v.strip()


def _validate_stazione_ref(v: str) -> str:
    """
    Accetta sia ID Viaggiatreno (es. 'S01700') sia nomi in chiaro (es. 'Tuscolana',
    'Roma Termini'). La risoluzione nome → ID avviene a runtime nel tool handler.
    """
    v = v.strip()
    if not v:
        raise ValueError("Il riferimento stazione non può essere vuoto.")
    return v


class MonitoraPartenzeInput(BaseModel):
    """Input per il monitoraggio delle partenze da una stazione."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    id_stazione: str = Field(
        ...,
        description=(
            "ID Viaggiatreno (es. 'S01700') oppure nome in chiaro della stazione "
            "(es. 'Tuscolana', 'Roma Termini', 'Centrale'). "
            "Se il nome è ambiguo verrà chiesta disambiguazione."
        ),
        min_length=2,
        max_length=100,
    )
    limite: Optional[int] = Field(
        default=10,
        description="Numero massimo di treni da restituire (default: 10, max: 30)",
        ge=1,
        le=30,
    )

    @field_validator("id_stazione")
    @classmethod
    def validate_id(cls, v: str) -> str:
        return _validate_stazione_ref(v)


class MonitoraArriviInput(BaseModel):
    """Input per il monitoraggio degli arrivi in una stazione."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    id_stazione: str = Field(
        ...,
        description=(
            "ID Viaggiatreno (es. 'S01700') oppure nome in chiaro della stazione "
            "(es. 'Tuscolana', 'Roma Termini', 'Centrale'). "
            "Se il nome è ambiguo verrà chiesta disambiguazione."
        ),
        min_length=2,
        max_length=100,
    )
    limite: Optional[int] = Field(
        default=10,
        description="Numero massimo di treni da restituire (default: 10, max: 30)",
        ge=1,
        le=30,
    )

    @field_validator("id_stazione")
    @classmethod
    def validate_id(cls, v: str) -> str:
        return _validate_stazione_ref(v)


class TracciaTrenoInput(BaseModel):
    """Input per il tracciamento in tempo reale di un singolo treno."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    numero_treno: str = Field(
        ...,
        description="Numero del treno (es. '9631' per Frecciarossa, '2342' per Regionale). Solo cifre.",
        min_length=1,
        max_length=10,
    )
    id_stazione_origine: str = Field(
        ...,
        description=(
            "ID Viaggiatreno (es. 'S01700') oppure nome in chiaro della stazione di origine "
            "(es. 'Milano Centrale', 'Termini'). Necessario per identificare univocamente il treno."
        ),
        min_length=2,
        max_length=100,
    )

    @field_validator("numero_treno")
    @classmethod
    def validate_numero(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("Il numero treno deve contenere solo cifre (es. '9631').")
        return v

    @field_validator("id_stazione_origine")
    @classmethod
    def validate_id(cls, v: str) -> str:
        return _validate_stazione_ref(v)


class OrariTraStazioniInput(BaseModel):
    """Input per la ricerca di treni tra due stazioni con orario teorico + real-time."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    stazione_a: str = Field(
        ...,
        description="Stazione di partenza/salita (nome in chiaro o ID, es. 'Tuscolana', 'Roma Termini')",
        min_length=2,
        max_length=100,
    )
    stazione_b: str = Field(
        ...,
        description="Stazione di arrivo/discesa (nome in chiaro o ID, es. 'Ponte Galeria', 'Fiumicino Aeroporto')",
        min_length=2,
        max_length=100,
    )
    orario_da: Optional[str] = Field(
        default=None,
        description="Orario minimo di partenza da stazione_a (formato HH:MM, es. '17:30'). Default: ora attuale.",
    )
    limite: Optional[int] = Field(
        default=10,
        description="Numero massimo di treni da mostrare (default 10, max 30)",
        ge=1,
        le=30,
    )

    @field_validator("orario_da")
    @classmethod
    def validate_orario(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        try:
            datetime.strptime(v, "%H:%M")
        except (ValueError, ImportError):
            raise ValueError("Formato orario non valido. Usa HH:MM (es. '17:30').")
        return v
