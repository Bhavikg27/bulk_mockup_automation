import cv2
import numpy as np
import os
from PIL import Image

# Paths
mockup_path = "tree.jpg"
designs_folder = "designs/"
output_folder = "mockups/"

# Destination points for the placeholder (corner coordinates in the mockup)
# Format: [(top-left x, y), (top-right x, y), (bottom-right x, y), (bottom-left x, y)]
destination_points = np.array([
    (660, 672),  # Top-left corner
    (1125, 672),  # Top-right corner
    (1125, 1318),  # Bottom-right corner
    (660, 1318)   # Bottom-left corner
], dtype=np.float32)

# Load the mockup template
mockup = cv2.imread(mockup_path)

# Create the output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Process each design
for design_file in os.listdir(designs_folder):
    if design_file.endswith(('.png', '.jpg', '.jpeg')):
        # Load the design
        design_path = os.path.join(designs_folder, design_file)
        design = cv2.imread(design_path)

        # Get the size of the design image
        h, w, _ = design.shape

        # Source points: the corners of the design image
        source_points = np.array([
            (0, 0),         # Top-left corner
            (w - 1, 0),     # Top-right corner
            (w - 1, h - 1), # Bottom-right corner
            (0, h - 1)      # Bottom-left corner
        ], dtype=np.float32)

        # Compute the perspective transform matrix
        matrix = cv2.getPerspectiveTransform(source_points, destination_points)

        # Warp the design image to fit the placeholder
        warped_design = cv2.warpPerspective(design, matrix, (mockup.shape[1], mockup.shape[0]), flags=cv2.INTER_CUBIC)

        # Create a binary mask of the placeholder area
        mask = np.zeros(mockup.shape[:2], dtype=np.uint8)
        cv2.fillConvexPoly(mask, destination_points.astype(np.int32), 255)

        # Combine the warped design with the mockup using the mask
        mask_inv = cv2.bitwise_not(mask)
        mockup_background = cv2.bitwise_and(mockup, mockup, mask=mask_inv)
        final_result = cv2.add(mockup_background, cv2.bitwise_and(warped_design, warped_design, mask=mask))

        # Save the output
        output_path = os.path.join(output_folder, f"tree_{design_file}")
        cv2.imwrite(output_path, final_result)

print("Mockup generation complete with precise placement!")