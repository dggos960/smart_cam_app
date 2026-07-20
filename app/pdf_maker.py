from PIL import Image
import os

def create_pdf_from_images(image_paths, output_filename):
    """
    Takes a list of image file paths and combines them into a single PDF.
    Saves the PDF to output_filename.
    """
    if not image_paths:
        print("No images provided to make a PDF.")
        return False

    try:
        images = []
        for path in image_paths:
            if os.path.exists(path):
                # Open image and convert to RGB (required for saving as PDF with Pillow)
                img = Image.open(path).convert('RGB')
                images.append(img)

        if not images:
            print("No valid images found.")
            return False

        first_image = images[0]
        # Save first image and append the rest
        if len(images) > 1:
            first_image.save(output_filename, save_all=True, append_images=images[1:])
        else:
            first_image.save(output_filename)

        print(f"PDF successfully created: {output_filename}")
        return True

    except Exception as e:
        print(f"Failed to create PDF: {e}")
        return False
