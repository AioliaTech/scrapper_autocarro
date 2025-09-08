Commit: Update test_client.py 
##########################################
### Download Github Archive Started...
### Mon, 08 Sep 2025 16:30:59 GMT
##########################################

#0 building with "default" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 811B done
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.11-slim
#2 DONE 0.4s

#3 [internal] load .dockerignore
#3 transferring context: 2B done
#3 DONE 0.0s

#4 [ 1/12] FROM docker.io/library/python:3.11-slim@sha256:1d6131b5d479888b43200645e03a78443c7157efbdb730e6b48129740727c312
#4 DONE 0.0s

#5 [internal] load build context
#5 transferring context: 97B done
#5 DONE 0.0s

#6 [ 5/12] COPY requirements.txt .
#6 CACHED

#7 [ 2/12] RUN apt-get update && apt-get install -y     wget     curl     gnupg     ca-certificates     && rm -rf /var/lib/apt/lists/*
#7 CACHED

#8 [ 3/12] RUN useradd --create-home --shell /bin/bash app
#8 CACHED

#9 [ 4/12] WORKDIR /app
#9 CACHED

#10 [ 6/12] RUN pip install --no-cache-dir -r requirements.txt
#10 CACHED

#11 [ 7/12] RUN playwright install chromium
#11 CACHED

#12 [ 8/12] RUN playwright install-deps
#12 0.383 BEWARE: your OS is not officially supported by Playwright; installing dependencies for ubuntu20.04-x64 as a fallback.
#12 0.384 Installing dependencies...
#12 0.435 Get:1 http://deb.debian.org/debian trixie InRelease [140 kB]
#12 0.452 Get:2 http://deb.debian.org/debian trixie-updates InRelease [47.1 kB]
#12 0.452 Get:3 http://deb.debian.org/debian-security trixie-security InRelease [43.4 kB]
#12 0.475 Get:4 http://deb.debian.org/debian trixie/main amd64 Packages [9669 kB]
#12 0.577 Get:5 http://deb.debian.org/debian trixie-updates/main amd64 Packages [2432 B]
#12 0.577 Get:6 http://deb.debian.org/debian-security trixie-security/main amd64 Packages [34.0 kB]
#12 1.227 Fetched 9936 kB in 1s (12.4 MB/s)
#12 1.227 Reading package lists...
#12 1.936 Reading package lists...
#12 2.714 Building dependency tree...
#12 2.959 Reading state information...
#12 2.998 Package ttf-ubuntu-font-family is not available, but is referred to by another package.
#12 2.998 This may mean that the package is missing, has been obsoleted, or
#12 2.998 is only available from another source
#12 2.998 
#12 2.998 Package libgdk-pixbuf2.0-0 is not available, but is referred to by another package.
#12 2.998 This may mean that the package is missing, has been obsoleted, or
#12 2.998 is only available from another source
#12 2.998 However the following packages replace it:
#12 2.998   libgdk-pixbuf-xlib-2.0-0
#12 2.998 
#12 2.998 Package libjpeg-turbo8 is not available, but is referred to by another package.
#12 2.998 This may mean that the package is missing, has been obsoleted, or
#12 2.998 is only available from another source
#12 2.998 
#12 2.998 Package ttf-unifont is not available, but is referred to by another package.
#12 2.998 This may mean that the package is missing, has been obsoleted, or
#12 2.998 is only available from another source
#12 2.998 However the following packages replace it:
#12 2.998   fonts-unifont
#12 2.998 
#12 3.003 E: Package 'ttf-unifont' has no installation candidate
#12 3.003 E: Package 'ttf-ubuntu-font-family' has no installation candidate
#12 3.003 E: Package 'libgdk-pixbuf2.0-0' has no installation candidate
#12 3.003 E: Unable to locate package libx264-155
#12 3.003 E: Unable to locate package libenchant1c2a
#12 3.003 E: Unable to locate package libicu66
#12 3.003 E: Package 'libjpeg-turbo8' has no installation candidate
#12 3.003 E: Unable to locate package libvpx6
#12 3.003 E: Unable to locate package libwebp6
#12 3.007 Failed to install browser dependencies
#12 3.007 Error: Installation process exited with code: 100
#12 ERROR: process "/bin/sh -c playwright install-deps" did not complete successfully: exit code: 1
------
 > [ 8/12] RUN playwright install-deps:
3.003 E: Package 'ttf-ubuntu-font-family' has no installation candidate
3.003 E: Package 'libgdk-pixbuf2.0-0' has no installation candidate
3.003 E: Unable to locate package libx264-155
3.003 E: Unable to locate package libenchant1c2a
3.003 E: Unable to locate package libicu66
3.003 E: Package 'libjpeg-turbo8' has no installation candidate
3.003 E: Unable to locate package libvpx6
3.003 E: Unable to locate package libwebp6
3.007 Failed to install browser dependencies
3.007 Error: Installation process exited with code: 100
------
Dockerfile:25
--------------------
  23 |     # Instalar navegadores do Playwright
  24 |     RUN playwright install chromium
  25 | >>> RUN playwright install-deps
  26 |     
  27 |     # Copiar código fonte
--------------------
ERROR: failed to solve: process "/bin/sh -c playwright install-deps" did not complete successfully: exit code: 1
##########################################
### Error
### Mon, 08 Sep 2025 16:31:03 GMT
##########################################

Command failed with exit code 1: docker buildx build --network host -f /etc/easypanel/projects/n8n/scrapper/code/Dockerfile -t easypanel/n8n/scrapper --label 'keep=true' --build-arg 'PORT=8000' --build-arg 'NODE_ENV=production' --build-arg 'LOG_LEVEL=INFO' --build-arg 'MAX_CONCURRENT_JOBS=3' --build-arg 'DEFAULT_DELAY=2' --build-arg 'DEFAULT_MAX_PAGES=50' --build-arg 'HEADLESS=true' --build-arg 'REQUEST_TIMEOUT=30000' --build-arg 'MAX_RETRIES=3' --build-arg 'RATE_LIMIT_REQUESTS=10' --build-arg 'RATE_LIMIT_WINDOW=60' --build-arg 'ENABLE_WEBHOOK_CALLBACKS=true' --build-arg 'EXTRACT_IMAGES=true' --build-arg 'EXTRACT_OPTIONALS=true' --build-arg 'DATA_RETENTION_DAYS=30' --build-arg 'LOG_RETENTION_DAYS=7' --build-arg 'AUTO_CLEANUP=true' --build-arg 'CORS_ORIGINS=*' --build-arg 'API_KEY_REQUIRED=false' --build-arg 'EASYPANEL_APP_NAME=scrapper' --build-arg 'DOMAIN=n8n-scrapper.xnvwew.easypanel.host' --build-arg 'GIT_SHA=812da3e2934e5b14309d08d0581eb45820dce710' /etc/easypanel/projects/n8n/scrapper/code/
