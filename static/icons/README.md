# Web App Icons Setup Guide

This directory should contain the following icon files for complete web app support:

## Required Icon Files

### Favicon Icons (for browser tabs)
- `favicon.ico` - Multi-size favicon (16x16, 32x32, etc.)
- `favicon-16x16.png` - 16x16px PNG favicon
- `favicon-32x32.png` - 32x32px PNG favicon

### Apple Touch Icons (for iOS home screen)
- `apple-touch-icon.png` - 180x180px (default)
- `apple-touch-icon-152x152.png` - 152x152px
- `apple-touch-icon-120x120.png` - 120x120px
- `apple-touch-icon-76x76.png` - 76x76px

### Android/Chrome Icons
- `android-chrome-192x192.png` - 192x192px
- `android-chrome-512x512.png` - 512x512px

### Microsoft Tile Icons (for Windows)
- `ms-icon-70x70.png` - 70x70px
- `ms-icon-144x144.png` - 144x144px (tile image)
- `ms-icon-150x150.png` - 150x150px
- `ms-icon-310x150.png` - 310x150px (wide tile)
- `ms-icon-310x310.png` - 310x310px (large tile)

## Design Recommendations

1. **Theme**: Use your app's primary color (#667eea) as background or accent
2. **Icon**: Consider using a book/journal icon with AI elements
3. **Format**: All icons should be in PNG format except favicon.ico
4. **Background**: Transparent or matching your theme color

## Tools for Icon Generation

You can create these icons using:
- **RealFaviconGenerator** (web-based)
- **Figma** or **Adobe Illustrator**
- **ImageMagick** or **GIMP**
- **Online icon generators**

## Installation After Creation

1. Add all icon files to this `/static/icons/` directory
2. The HTML template already references all these icons
3. Test on different devices and browsers
4. Your web app will now have proper icons across all platforms!
