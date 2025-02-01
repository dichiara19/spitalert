import click
import asyncio
from .scripts.init_hospitals import init_hospitals
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@click.group()
def cli():
    """CLI per la gestione di SpitAlert."""
    pass

@cli.command()
def init():
    """Inizializza o aggiorna i dati degli ospedali nel database."""
    click.echo("Inizializzazione ospedali...")
    asyncio.run(init_hospitals())
    click.echo("Inizializzazione completata!")

if __name__ == '__main__':
    cli() 