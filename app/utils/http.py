from typing import Optional, Dict, Any
import httpx
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import logging
from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class HTTPClient:
    def __init__(
        self,
        timeout: float = None,
        max_retries: int = None,
        headers: Dict[str, str] = None
    ):
        self.timeout = timeout or settings.HTTP_TIMEOUT
        self.max_retries = max_retries or settings.HTTP_MAX_RETRIES
        self.headers = {
            'User-Agent': settings.HTTP_USER_AGENT,
            **(headers or {})
        }
        
    @retry(
        retry=retry_if_exception_type((
            httpx.TimeoutException,
            httpx.TransportError,
            httpx.NetworkError,
            asyncio.TimeoutError
        )),
        stop=stop_after_attempt(settings.HTTP_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        before_sleep=lambda retry_state: logger.warning(
            f"Tentativo {retry_state.attempt_number} fallito, "
            f"nuovo tentativo tra {retry_state.next_action.sleep} secondi"
        )
    )
    async def get(
        self,
        url: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: float = None
    ) -> httpx.Response:
        """
        Esegue una richiesta GET con retry e timeout.
        
        Args:
            url: URL della richiesta
            params: Parametri query string
            headers: Headers aggiuntivi
            timeout: Timeout specifico per questa richiesta
            
        Returns:
            httpx.Response: Risposta della richiesta
            
        Raises:
            httpx.HTTPError: In caso di errore HTTP
        """
        merged_headers = {**self.headers, **(headers or {})}
        timeout_value = timeout or self.timeout
        
        try:
            async with httpx.AsyncClient(
                timeout=timeout_value,
                headers=merged_headers
            ) as client:
                logger.debug(
                    f"Esecuzione richiesta GET a {url} "
                    f"(timeout={timeout_value}s, headers={merged_headers})"
                )
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response
                
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Errore HTTP {e.response.status_code} per {url}: "
                f"{e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Errore durante la richiesta a {url}: {str(e)}")
            raise

    async def get_text(
        self,
        url: str,
        **kwargs
    ) -> str:
        """
        Esegue una richiesta GET e restituisce il testo della risposta.
        
        Args:
            url: URL della richiesta
            **kwargs: Parametri aggiuntivi per il metodo get()
            
        Returns:
            str: Testo della risposta
        """
        response = await self.get(url, **kwargs)
        return response.text
        
    async def get_json(
        self,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Esegue una richiesta GET e restituisce il JSON della risposta.
        
        Args:
            url: URL della richiesta
            **kwargs: Parametri aggiuntivi per il metodo get()
            
        Returns:
            Dict[str, Any]: JSON della risposta
        """
        response = await self.get(url, **kwargs)
        return response.json() 