"""Corre las cuatro cajas y escribe BOXES.md con todo lo que va al póster.

Cada caja se presenta con las cuatro cosas que hay que enseñar: el fichero o ficheros de
entrada, el código, la salida de consola y el fichero o ficheros de salida. Nada se
teclea a mano — lo que se pega en el póster es lo que estos scripts imprimen de verdad.

    cd publications/ICCCM26/poster/boxes && python build.py
    python build.py --check      # falla si BOXES.md no está al día (para CI)
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CAJAS = ["box1_read.py", "box2_write.py", "box3_loss.py", "box4_roundtrip.py"]


def corre(script: Path) -> tuple[str, str, list[Path]]:
    """Ejecuta una caja y devuelve (título, salida de consola, ficheros que ha creado).

    `out/` se vacía antes de empezar, así que lo que aparece después de correr una caja
    es suyo. Comparar contenidos no vale: una segunda pasada escribe lo mismo y parecería
    que la caja no genera nada.
    """
    antes = set((AQUI / "out").glob("*"))
    hecho = subprocess.run([sys.executable, script.name], cwd=AQUI,
                           capture_output=True, text=True, check=True)
    nuevos = sorted(set((AQUI / "out").glob("*")) - antes)

    codigo = script.read_text(encoding="utf-8")
    titulo = codigo.split('"""')[1].splitlines()[0]
    return titulo, hecho.stdout.rstrip("\n"), nuevos


def sin_docstring(codigo: str) -> str:
    """El código que se enseña: sin el docstring, que ya es el título de la caja."""
    return re.sub(r'^"""[\s\S]*?"""\n', "", codigo).strip()


def bloque(titulo: str, cuerpo: str, lenguaje: str = "") -> str:
    return f"**{titulo}**\n\n```{lenguaje}\n{cuerpo}\n```\n"


def markdown() -> str:
    for viejo in (AQUI / "out").glob("*"):
        viejo.unlink()
    fuera = [
        "# Las cuatro cajas de código del póster\n",
        "Columna derecha del A0. Cada caja lleva las cuatro cosas en este orden: "
        "**input · code · console · output**. Las etiquetas van en inglés porque se "
        "imprimen. Una caja cuyo resultado *es* la consola no repite un fichero de "
        "salida con lo mismo dentro.\n",
        "Se regenera con `cd publications/ICCCM26/poster/boxes && python build.py`. "
        "Nada está tecleado a mano.\n",
    ]
    for n, nombre in enumerate(CAJAS, start=1):
        script = AQUI / nombre
        titulo, consola, salidas = corre(script)
        # Qué lee la caja: cualquier fichero de `in/` cuyo nombre aparezca en su código.
        # Vale igual si la ruta está compuesta (`f"in/{fichero}"`), que es lo normal
        # cuando una caja lee varios.
        fuente = script.read_text()
        entradas = [e.name for e in sorted((AQUI / "in").iterdir()) if e.name in fuente]

        fuera.append(f"\n---\n\n## {titulo}\n")
        for e in entradas:
            fuera.append(bloque(f"input · in/{e}",
                                (AQUI / "in" / e).read_text().rstrip()))
        fuera.append(bloque(f"code · {nombre}",
                            sin_docstring(script.read_text()), "python"))
        fuera.append(bloque("console", consola))
        for s in salidas:
            fuera.append(bloque(f"output · out/{s.name}", s.read_text().rstrip()))
    return "\n".join(fuera)


if __name__ == "__main__":
    destino = AQUI / "BOXES.md"
    nuevo = markdown()
    if "--check" in sys.argv:
        viejo = destino.read_text(encoding="utf-8") if destino.exists() else ""
        if viejo != nuevo:
            sys.exit("BOXES.md está desfasado — corre `python build.py`")
        print("BOXES.md al día")
    else:
        destino.write_text(nuevo, encoding="utf-8")
        print(f"{destino.relative_to(AQUI.parent.parent)} — {len(CAJAS)} cajas")
