# Mistral OCR Converter

This is a simple wrapper to utilize the Mistral OCR API to convert PDFs to markdown files. It was created through adapting the code available on the Colab notebook shared by Mistral, to make it easier to use in a day-to-day basis. 

Anyone can get a free API key at Mistral's console, [La Plateforme](https://console.mistral.ai/home). 

To build it to utilize as a standalone app (with persistent API key storage), in the same directory, run: 

```bash
pyinstaller --windowed --noconsole --name "Mistral OCR" tomarkdown. py
```

You can change the name or any of the flags as you desire. 

For terms of use, please check the license file. 
