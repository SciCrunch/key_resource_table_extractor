package sciscore.key_resource_table_extractor;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import sciscore.key_resource_table_extractor.common.Rectangle;

import java.awt.*;
import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class PDFUtils {


    public static Map<Integer, Rectangle> getPageBounds(String pdfFile) throws Exception {
        Map<Integer, Rectangle> map = new HashMap<>();

        PDDocument document = null;
        int numPages;
        try {
            document = Loader.loadPDF(new File(pdfFile));
            numPages = document.getNumberOfPages();
            for (int n = 0; n < numPages; n++) {
                PDPage page = document.getPage(n);
                PDRectangle cropBox = page.getCropBox();
                Rectangle rect = new Rectangle(cropBox.getLowerLeftY(),
                        cropBox.getLowerLeftX(), cropBox.getWidth(),
                        cropBox.getHeight());
                map.put(n, rect);
            }
        } finally {
            if (document != null) {
                document.close();
            }
        }
        return map;
    }

    public static void rectangles2PDF(List<Rectangle> rectList, String outPDFFile
                                      ) throws Exception{
        PDDocument linePDF = new PDDocument();
        PDPage newPage = new PDPage();
        linePDF.addPage(newPage);
        PDPageContentStream contentStream = new PDPageContentStream(
                linePDF, newPage, PDPageContentStream.AppendMode.APPEND, false);
        float page_height = newPage.getCropBox().getUpperRightY();

        for (Rectangle rect : rectList) {
            String x = Double.toString(rect.getX());
            // String y = Double.toString(page_height - rect.getY()); // orig
            String y = Double.toString(rect.getY());
            String w = Double.toString(rect.getWidth());
            String h = Double.toString(rect.getHeight());
            addLine(contentStream, page_height, Float.parseFloat(x),
                    Float.parseFloat(y), Float.parseFloat(w),
                    Float.parseFloat(h));
        }
        contentStream.close();
        linePDF.save(outPDFFile);
        System.out.println("saved " + outPDFFile);
        linePDF.close();
    }

    public static void addLine(PDPageContentStream contentStream, float pageHeight,
                               float x, float y,
                               float w, float h) throws Exception {
        contentStream.setStrokingColor(Color.BLACK);
        if (pageHeight > 0) {
            y = pageHeight - y;
        }
        contentStream.addRect(x, y, w, h);
        contentStream.stroke();
    }
}
