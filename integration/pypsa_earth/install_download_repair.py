"""Apply narrowly scoped, idempotent fixes to the inspected Earth checkout."""
from pathlib import Path
import argparse
import shutil

HERE = Path(__file__).resolve().parent


def main(earth):
    scripts = earth / "scripts"
    backup = earth / ".cache/sudan-download-repair-originals"
    backup.mkdir(parents=True, exist_ok=True)
    exclude = earth / ".git/info/exclude"
    if exclude.parent.exists():
        contents = exclude.read_text() if exclude.exists() else ""
        for entry in ["/.cache/sudan-downloads/", "/.cache/sudan-download-repair-originals/"]:
            if entry not in contents.splitlines():
                contents += "\n" + entry + "\n"
        exclude.write_text(contents)
    for name in ["_helpers.py", "retrieve_databundle_light.py"]:
        path = scripts / name
        dest = backup / name
        if not dest.exists():
            shutil.copy2(path, dest)
    helper = scripts / "_helpers.py"
    text = helper.read_text()
    start = text.index("def progress_retrieve(")
    end = text.index("\ndef content_retrieve(", start)
    text = text[:start] + '''def progress_retrieve(
    url, file, data=None, headers=None, disable_progress=False, roundto=1.0,
):
    """Sudan local repair: cached streaming, verified TLS and explicit retries."""
    from sudan_downloads import retrieve
    return retrieve(url, file, data, headers, disable_progress, roundto)

''' + text[end:]
    helper.write_text(text)
    path = scripts / "retrieve_databundle_light.py"
    text = path.read_text()
    text = text.replace(
        '''        except:
            logger.warning(f"Failed download resource '{resource}' from cloud '{url}'.")''',
        '''        except Exception:
            logger.exception(f"Failed download resource '{resource}' from cloud '{url}'.")''')
    text = text.replace(
        '''    if len(hydrobasin_bundles) > 0:
        if not config_bundles[hydrobasin_bundles[0]]["tutorial"]:
            logger.info("Merging regional hydrobasins files into a global shapefile")''',
        '''    if len(hydrobasin_bundles) > 0 and hydrobasin_bundles[0] in downloaded_bundles:
        if not config_bundles[hydrobasin_bundles[0]]["tutorial"]:
            logger.info("Merging regional hydrobasins files into a global shapefile")''')
    anchor = '''    missing_bundles = set(bundles_to_download) - set(downloaded_bundles)
    if missing_bundles:
'''
    replacement = anchor + '''        raise RuntimeError("Required bundles failed: " + ", ".join(sorted(missing_bundles)))
'''
    if replacement not in text:
        assert text.count(anchor) == 1
        text = text.replace(anchor, replacement)
    text = text.replace(
        '# starting from the next month to check the current and the previous after',
        '# Start with the current month, then try prior releases.')
    # Start at this month, avoiding an unnecessary future-month attempt.
    text = text.replace('dt.datetime.today() + dt.timedelta(days=31)', 'dt.datetime.today()')
    path.write_text(text)
    shutil.copy2(HERE / "sudan_downloads.py", scripts / "sudan_downloads.py")
    print("Installed download repair; originals saved under", backup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--earth", type=Path, required=True)
    main(parser.parse_args().earth.resolve())
