#!/usr/bin/env python3
"""Generate and build the gurren_lagann_mod Fabric project."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

PROJECT_NAME = "gurren_lagann_mod"
MOD_ID = "gurren_lagann_mod"
GROUP = "com.gurrenlagann"
VERSION = "1.0.0"
MC_VERSION = "1.20.1"
YARN_MAPPINGS = "1.20.1+build.10"
LOADER_VERSION = "0.15.11"
FABRIC_API_VERSION = "0.92.2+1.20.1"
JAVA_CLASS = "GurrenLagannMod"
PACKAGE = "com.gurrenlagann.mod"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str | bytes) -> None:
    ensure_dir(path.parent)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def run_cmd(cmd: list[str], cwd: Path, error_message: str) -> None:
    print(f"[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"{error_message} (exit code: {result.returncode})")


def check_java() -> None:
    try:
        result = subprocess.run(
            ["java", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Java не найден. Установите JDK 17+ и добавьте java в PATH."
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"Java установлен некорректно. Вывод: {result.stderr.strip() or result.stdout.strip()}"
        )


def ensure_pillow() -> None:
    try:
        __import__("PIL")
        return
    except ImportError:
        pass

    print("[INFO] Pillow не найден, пробую установить через pip...")
    install_cmd = [sys.executable, "-m", "pip", "install", "Pillow"]
    proc = subprocess.run(install_cmd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            "Не удалось установить Pillow автоматически. "
            "Установите вручную: python -m pip install Pillow"
        )

    try:
        __import__("PIL")
    except ImportError as exc:
        raise RuntimeError(
            "Pillow всё ещё недоступен после установки. Проверьте Python окружение."
        ) from exc


def project_paths(root: Path) -> dict[str, Path]:
    src_main = root / "src" / "main"
    return {
        "root": root,
        "java": src_main / "java",
        "resources": src_main / "resources",
        "assets": src_main / "resources" / "assets" / MOD_ID,
        "models": src_main / "resources" / "assets" / MOD_ID / "models" / "item",
        "textures": src_main / "resources" / "assets" / MOD_ID / "textures" / "item",
        "lang": src_main / "resources" / "assets" / MOD_ID / "lang",
    }


def item_definitions() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    def add(prefix: str, count: int, title: str, category: str) -> None:
        for i in range(1, count + 1):
            item_id = f"{prefix}_{i:02d}"
            items.append(
                {
                    "id": item_id,
                    "name": f"{title} {i:02d}",
                    "category": category,
                }
            )

    add("drill", 10, "Drill", "drill")
    add("core", 10, "Core", "core")
    add("part", 10, "Mecha Part", "part")
    add("cape", 5, "Team Cape", "cape")
    add("blade", 5, "Spiral Blade", "blade")
    add("glasses", 5, "Kamina Glasses", "glasses")
    return items


def generate_java_sources(java_root: Path, items: list[dict[str, str]]) -> None:
    package_dir = java_root / Path(PACKAGE.replace(".", "/"))
    ensure_dir(package_dir)

    register_lines = []
    decl_lines = []
    for item in items:
        const_name = item["id"].upper()
        decl_lines.append(
            f'    public static final Item {const_name} = registerItem("{item["id"]}");'
        )
        register_lines.append(f"        ITEMS.add({const_name});")

    java_content = f'''package {PACKAGE};

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.item.v1.FabricItemSettings;
import net.minecraft.item.Item;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.util.Identifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

public class {JAVA_CLASS} implements ModInitializer {{
    public static final String MOD_ID = "{MOD_ID}";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);
    private static final List<Item> ITEMS = new ArrayList<>();

{os.linesep.join(decl_lines)}

    private static Item registerItem(String id) {{
        Item item = Registry.register(Registries.ITEM, new Identifier(MOD_ID, id), new Item(new FabricItemSettings()));
        return item;
    }}

    @Override
    public void onInitialize() {{
{os.linesep.join(register_lines)}
        LOGGER.info("Initialized {{}} with {{}} themed items.", MOD_ID, ITEMS.size());
    }}
}}
'''
    write_file(package_dir / f"{JAVA_CLASS}.java", java_content)


def generate_models(models_dir: Path, items: Iterable[dict[str, str]]) -> None:
    for item in items:
        model = {
            "parent": "item/generated",
            "textures": {"layer0": f"{MOD_ID}:item/{item['id']}"},
        }
        write_file(models_dir / f"{item['id']}.json", json.dumps(model, indent=2) + "\n")


def generate_texture(texture_path: Path, category: str) -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if category == "drill":
        for y in range(16):
            for x in range(16):
                v = (x + y) % 4
                color = (220 - v * 30, 180 - v * 20, 60 + v * 20, 255)
                if (x + y) % 2 == 0:
                    img.putpixel((x, y), color)
        draw.line((0, 15, 15, 0), fill=(255, 240, 120, 255), width=1)
    elif category == "core":
        for y in range(16):
            for x in range(16):
                dx = x - 7.5
                dy = y - 7.5
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < 7.5:
                    tone = int(max(0, 255 - dist * 22))
                    img.putpixel((x, y), (tone, 80, 255, 255))
        draw.ellipse((4, 4, 11, 11), outline=(255, 200, 255, 255), width=1)
    elif category == "part":
        draw.rectangle((1, 1, 14, 14), fill=(70, 80, 90, 255), outline=(140, 160, 170, 255))
        for x in range(3, 14, 4):
            draw.line((x, 2, x, 13), fill=(40, 45, 50, 255), width=1)
        for y in range(3, 14, 4):
            draw.line((2, y, 13, y), fill=(110, 120, 130, 255), width=1)
    elif category == "cape":
        for y in range(16):
            stripe = (y // 3) % 2
            color = (190, 20, 30, 255) if stripe == 0 else (120, 8, 16, 255)
            draw.line((0, y, 15, y), fill=color, width=1)
        draw.rectangle((1, 1, 14, 14), outline=(255, 220, 220, 255), width=1)
    elif category == "blade":
        draw.polygon([(2, 14), (12, 2), (14, 4), (4, 15)], fill=(210, 220, 235, 255))
        draw.line((3, 14, 13, 3), fill=(255, 255, 255, 255), width=1)
        draw.rectangle((0, 13, 4, 15), fill=(120, 70, 20, 255))
    elif category == "glasses":
        draw.rectangle((1, 5, 6, 10), fill=(255, 80, 90, 255), outline=(30, 20, 20, 255))
        draw.rectangle((9, 5, 14, 10), fill=(255, 80, 90, 255), outline=(30, 20, 20, 255))
        draw.rectangle((6, 7, 9, 8), fill=(30, 20, 20, 255))
        draw.line((0, 7, 1, 7), fill=(30, 20, 20, 255), width=1)
        draw.line((14, 7, 15, 7), fill=(30, 20, 20, 255), width=1)
    else:
        draw.rectangle((0, 0, 15, 15), fill=(255, 0, 255, 255))

    img.save(texture_path, format="PNG")


def generate_assets(paths: dict[str, Path], items: list[dict[str, str]]) -> None:
    fabric_mod_json = {
        "schemaVersion": 1,
        "id": MOD_ID,
        "version": VERSION,
        "name": "Gurren Lagann Mod",
        "description": "A Fabric mod with many themed items inspired by Gurren Lagann.",
        "authors": ["Auto Generated"],
        "environment": "*",
        "entrypoints": {
            "main": [f"{PACKAGE}.{JAVA_CLASS}"]
        },
        "depends": {
            "fabricloader": f">={LOADER_VERSION}",
            "minecraft": f"~{MC_VERSION}",
            "java": ">=17",
            "fabric-api": "*"
        }
    }
    write_file(paths["resources"] / "fabric.mod.json", json.dumps(fabric_mod_json, indent=2) + "\n")

    lang = {f"item.{MOD_ID}.{item['id']}": item["name"] for item in items}
    write_file(paths["lang"] / "en_us.json", json.dumps(lang, indent=2) + "\n")

    generate_models(paths["models"], items)
    for item in items:
        generate_texture(paths["textures"] / f"{item['id']}.png", item["category"])


def generate_gradle_files(root: Path) -> None:
    settings = f'''pluginManagement {{
    repositories {{
        maven {{ url = "https://maven.fabricmc.net/" }}
        gradlePluginPortal()
        mavenCentral()
    }}
}}

rootProject.name = "{PROJECT_NAME}"
'''

    build_gradle = f'''plugins {{
    id 'fabric-loom' version '1.6-SNAPSHOT'
    id 'maven-publish'
}}

version = project.mod_version
group = project.maven_group

base {{
    archivesName = project.archives_base_name
}}

repositories {{
    maven {{ url = "https://maven.fabricmc.net/" }}
    mavenCentral()
}}

dependencies {{
    minecraft "com.mojang:minecraft:${{project.minecraft_version}}"
    mappings "net.fabricmc:yarn:${{project.yarn_mappings}}:v2"
    modImplementation "net.fabricmc:fabric-loader:${{project.loader_version}}"
    modImplementation "net.fabricmc.fabric-api:fabric-api:${{project.fabric_version}}"
}}

java {{
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}}

tasks.withType(JavaCompile).configureEach {{
    it.options.release = 17
}}

processResources {{
    inputs.property "version", project.version
    filesMatching("fabric.mod.json") {{
        expand "version": project.version
    }}
}}

jar {{
    from("LICENSE") {{
        rename {{ "${{it}}_${{project.base.archivesName.get()}}" }}
    }}
}}
'''

    gradle_props = f'''org.gradle.jvmargs=-Xmx2G
org.gradle.parallel=true

minecraft_version={MC_VERSION}
yarn_mappings={YARN_MAPPINGS}
loader_version={LOADER_VERSION}
fabric_version={FABRIC_API_VERSION}

mod_version={VERSION}
maven_group={GROUP}
archives_base_name={PROJECT_NAME}
'''

    write_file(root / "settings.gradle", settings)
    write_file(root / "build.gradle", build_gradle)
    write_file(root / "gradle.properties", gradle_props)
    write_file(root / "LICENSE", "Generated project license placeholder.\n")


def ensure_gradle_wrapper(root: Path) -> None:
    gradlew = root / ("gradlew.bat" if os.name == "nt" else "gradlew")
    wrapper_jar = root / "gradle" / "wrapper" / "gradle-wrapper.jar"
    wrapper_props = root / "gradle" / "wrapper" / "gradle-wrapper.properties"

    if gradlew.exists() and wrapper_jar.exists() and wrapper_props.exists():
        return

    gradle_cmd = shutil.which("gradle")
    if not gradle_cmd:
        raise RuntimeError(
            "Gradle не найден в PATH. Установите Gradle (для генерации wrapper) "
            "или добавьте gradle в PATH и запустите снова."
        )

    run_cmd([gradle_cmd, "wrapper", "--gradle-version", "8.8"], root, "Не удалось сгенерировать Gradle wrapper")


def run_build(root: Path) -> Path:
    gradlew = "gradlew.bat" if os.name == "nt" else "./gradlew"
    run_cmd([gradlew, "build"], root, "Сборка мода завершилась с ошибкой")

    libs = root / "build" / "libs"
    jars = sorted(libs.glob("*.jar"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not jars:
        raise RuntimeError("Сборка завершилась, но jar не найден в build/libs")
    return jars[0]


def main() -> None:
    check_java()
    ensure_pillow()

    root = Path.cwd() / PROJECT_NAME
    ensure_dir(root)

    paths = project_paths(root)
    for key, path in paths.items():
        if key != "root":
            ensure_dir(path)

    items = item_definitions()
    generate_gradle_files(root)
    generate_java_sources(paths["java"], items)
    generate_assets(paths, items)
    ensure_gradle_wrapper(root)
    jar_path = run_build(root)

    print("\nГотово!")
    print(f"Проект: {root}")
    print(f"JAR: {jar_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
