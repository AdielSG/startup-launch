"""
Script de prueba para el actor supreme_coder/linkedin-post (Wpp1BZ6yGWjySadk3).

Uso:
  python test_apify.py <linkedin_post_url>

Ejemplo:
  python test_apify.py "https://www.linkedin.com/posts/satyanadella_ai-activity-7198338166445973504-abcd"
"""
import asyncio
import json
import sys

from apify_client import ApifyClientAsync
from config import settings

ACTOR_ID = "Wpp1BZ6yGWjySadk3"


async def test(post_url: str):
    token = settings.apify_api_token
    if not token:
        print("ERROR: APIFY_API_TOKEN no esta configurado en .env")
        return

    print(f"Token : {token[:12]}...")
    print(f"Actor : {ACTOR_ID}")
    print(f"URL   : {post_url}")
    print()

    run_input = {
        "urls":                        [post_url],
        "limitPerSource":              1,
        "scrapeUntilDate":             None,
        "scrapeAdditionalInformation": True,
        "getRowData":                  False,
    }

    print("Input que se envia:")
    print(json.dumps(run_input, indent=2))
    print()
    print("Llamando al actor... (puede tardar hasta 60 s)")
    print()

    try:
        client = ApifyClientAsync(token=token)
        run = await client.actor(ACTOR_ID).call(run_input=run_input)

        if not run:
            print("ERROR: el actor devolvio None — fallo antes de arrancar.")
            return

        print(f"Run ID : {run.get('id')}")
        print(f"Status : {run.get('status')}")
        print()

        items = (await client.dataset(run["defaultDatasetId"]).list_items()).items
        print(f"Items devueltos: {len(items)}")
        print()

        if not items:
            print("RESULTADO: 0 items — el actor no encontro datos para esta URL.")
            print("Posibles causas:")
            print("  - La URL no es un post publico de LinkedIn")
            print("  - El formato de la URL es incorrecto")
            return

        item = items[0]

        print("=== Respuesta completa del actor ===")
        print(json.dumps(item, indent=2, default=str))
        print()

        # Campos de engagement que nos interesan
        engagement_keys = [
            "numLikes", "likeCount", "likes",
            "numShares", "shareCount", "numReposts", "repostCount", "reposts",
            "numComments", "commentCount", "comments",
            "publishedAt", "postedAt", "date", "createdAt",
        ]

        print("=== Campos de engagement encontrados ===")
        found = {k: item[k] for k in engagement_keys if k in item}
        if found:
            for k, v in found.items():
                print(f"  {k}: {v}")
        else:
            print("  Ninguno de los campos esperados encontrado.")
            print("  Todas las keys disponibles:", list(item.keys()))

    except Exception as exc:
        print(f"ERROR: {exc}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_apify.py <linkedin_post_url>")
        print()
        print("Ejemplo:")
        print('  python test_apify.py "https://www.linkedin.com/posts/satyanadella_ai-activity-7198338166445973504-abcd"')
        sys.exit(1)

    asyncio.run(test(sys.argv[1]))
