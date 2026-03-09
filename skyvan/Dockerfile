# Use an official Python runtime with Alpine Linux as a parent image
FROM python:3.9-alpine

# Set environment variables for Python
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# ---- System deps ----
#  - WeasyPrint runtime: pango, cairo, gdk-pixbuf, glib, harfbuzz, fribidi, cairo-gobject
#  - SVG + MIME: librsvg, shared-mime-info
#  - Fonts to avoid tofu boxes: DejaVu + Liberation
#  - Your existing build deps (lxml, mysql/mariadb, etc.)
RUN apk add --no-cache \
    # your existing build tools
    git gcc python3-dev libxml2-dev libxslt-dev build-base py3-lxml zlib-dev \
    mariadb-connector-c-dev wget \
    # weasyprint runtime stack
    pango gdk-pixbuf cairo cairo-gobject libffi glib harfbuzz fribidi \
    librsvg shared-mime-info \
    # fonts
    ttf-dejavu ttf-liberation

# (Optional) upgrade pip to get manylinux wheels where possible
RUN pip install --no-cache-dir --upgrade pip

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8000 for the Django application
EXPOSE 8000

# Run Django's development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
