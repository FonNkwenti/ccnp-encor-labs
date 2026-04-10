import os
import subprocess
import argparse

DRAWIO_PATH = "/Applications/draw.io.app/Contents/MacOS/draw.io"

def export_file(drawio_file, output_path=None, scale=2):
    """
    Exports a single .drawio file to PNG.
    """
    if not output_path:
        output_path = os.path.splitext(drawio_file)[0] + ".png"
    
    print(f"Exporting {drawio_file} -> {output_path}...")
    
    try:
        subprocess.run([
            DRAWIO_PATH,
            "-x",
            "-f", "png",
            "-t",
            "-s", str(scale),
            drawio_file,
            "-o", output_path
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error exporting {drawio_file}: {e}")
        return False

def batch_export(root_dir, scale=2):
    """
    Recursively finds and exports all .drawio files in root_dir.
    """
    success_count = 0
    fail_count = 0
    
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".drawio"):
                full_path = os.path.join(root, file)
                if export_file(full_path, scale=scale):
                    success_count += 1
                else:
                    fail_count += 1
                    
    print(f"
Batch export complete.")
    print(f"Successfully exported: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch export Draw.io diagrams to PNG.")
    parser.add_argument("--dir", default="labs", help="Directory to search for .drawio files (default: labs)")
    parser.add_argument("--scale", type=int, default=2, help="Export scale/zoom (default: 2)")
    parser.add_argument("--file", help="Export a specific file only")
    
    args = parser.parse_args()
    
    if not os.path.exists(DRAWIO_PATH):
        print(f"Error: Draw.io CLI not found at {DRAWIO_PATH}")
        exit(1)
        
    if args.file:
        export_file(args.file, scale=args.scale)
    else:
        batch_export(args.dir, scale=args.scale)
