package sciscore.key_resource_table_extractor;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.contentstream.PDFGraphicsStreamEngine;
import org.apache.pdfbox.cos.COSName;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.graphics.color.PDColor;
import org.apache.pdfbox.pdmodel.graphics.image.PDImage;
import sciscore.key_resource_table_extractor.common.Rectangle;

import java.awt.geom.GeneralPath;
import java.awt.geom.Point2D;
import java.awt.geom.Rectangle2D;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class LineExtractor {

    public static Map<Integer, List<Rectangle>> extractLines(String pdfFile) throws Exception {
        Map<Integer, List<Rectangle>> map = new HashMap<>();
        PDDocument document = null;
        int numPages;
        double pageHeight;
        try {
            // document = PDDocument.load(new File(pdfFile));
            document = Loader.loadPDF(new File(pdfFile));

            numPages = document.getNumberOfPages();
            System.out.println("Line Processing numPages:" + numPages);
            for (int n = 0; n < numPages; n++) {
                System.out.println("Line Processing page:" + n);
                PDPage page = document.getPage(n);
                pageHeight = page.getCropBox().getUpperRightY();
                System.out.println("page_height:" + pageHeight);
                List<Rectangle2D> rectList = new ArrayList<>();
                LineCatcher lineCatcher = new LineCatcher(page, rectList);
                lineCatcher.processPage(page);
                List<Rectangle> rectangles = new ArrayList<>(rectList.size());
                for (Rectangle2D rect : rectList) {
                    double x = rect.getX();
                    double y = pageHeight - rect.getY(); // orig
                    double w = rect.getWidth();
                    double h = rect.getHeight();
                    rectangles.add(new Rectangle((float) y, (float) x,
                            (float) w, (float) h));
                }
                // rectangles = clipHeight(rectangles, pageHeight);
                map.put(n, rectangles);
            }
        } finally {
            if (document != null) {
                document.close();
            }
        }
        return map;
    }


    public static List<Rectangle> clipHeight(List<Rectangle> rectList, double pageHeight) {
        List<Rectangle> clippedList = new ArrayList<>(rectList.size());
        for(Rectangle rect : rectList) {
            if (rect.getBottom() > pageHeight) {
                double height = pageHeight - rect.getY();
                Rectangle clipped = new Rectangle(rect.getTop(), rect.getLeft(), (float) rect.getWidth(),
                        (float)height);
                clippedList.add(clipped);
            } else {
                clippedList.add(rect);
            }
        }

        return clippedList;
    }

    /**
     * @author Tilman Hausherr
     * @author Yashodhan Joglekar
     */
    public static class LineCatcher extends PDFGraphicsStreamEngine {
        private final GeneralPath linePath = new GeneralPath();
        private int clipWindingRule = -1;
        private List<Rectangle2D> rectList;
        int linesCount = 0;
        private static final int COLOR_WHITE = 16777215;

        public LineCatcher(PDPage page, List<Rectangle2D> rectList) {
            super(page);
            this.rectList = rectList;
        }

        public List<Rectangle2D> getRectList() {
            return rectList;
        }

        @Override
        public void appendRectangle(Point2D p0, Point2D p1, Point2D p2, Point2D p3) throws IOException {
            // to ensure that the path is created in the right direction, we have to create
            // it by combining single lines instead of creating a simple rectangle
            linePath.moveTo((float) p0.getX(), (float) p0.getY());
            linePath.lineTo((float) p1.getX(), (float) p1.getY());
            linePath.lineTo((float) p2.getX(), (float) p2.getY());
            linePath.lineTo((float) p3.getX(), (float) p3.getY());

            // close the subpath instead of adding the last line so that a possible set line
            // cap style isn't taken into account at the "beginning" of the rectangle
            linePath.closePath();
            //IBO
            PDColor strokingColor = getGraphicsState().getStrokingColor();
            if (strokingColor.toRGB() != COLOR_WHITE) {
                rectList.add(new Rectangle2D.Float((float) p0.getX(),
                        (float) p0.getY(),
                        (float) (p1.getX() - p0.getX()),
                        (float) (p2.getY() - p1.getY())));
            }
        }

        @Override
        public void drawImage(PDImage pdi) throws IOException {
        }

        @Override
        public void clip(int windingRule) throws IOException {
            // the clipping path will not be updated until the succeeding painting operator is called
            clipWindingRule = windingRule;

        }

        @Override
        public void moveTo(float x, float y) throws IOException {
            linePath.moveTo(x, y);
        }

        @Override
        public void lineTo(float x, float y) throws IOException {
            linePath.lineTo(x, y);
            linesCount++;
        }

        @Override
        public void curveTo(float x1, float y1, float x2, float y2, float x3, float y3) throws IOException {
            linePath.curveTo(x1, y1, x2, y2, x3, y3);
            linesCount = 0;
        }

        @Override
        public Point2D getCurrentPoint() throws IOException {
            return linePath.getCurrentPoint();
        }

        @Override
        public void closePath() throws IOException {
            if (linesCount == 3) {
                PDColor strokingColor = getGraphicsState().getStrokingColor();
                if (strokingColor.toRGB() != COLOR_WHITE) {
                    java.awt.Rectangle bounds = linePath.getBounds();
                    rectList.add(bounds);
                }

            }
            linesCount = 0;

            linePath.closePath();
        }

        @Override
        public void endPath() throws IOException {
            if (clipWindingRule != -1) {
                linePath.setWindingRule(clipWindingRule);
                getGraphicsState().intersectClippingPath(linePath);
                clipWindingRule = -1;
            }
            if (linesCount == 3) {
                PDColor strokingColor = getGraphicsState().getStrokingColor();
                if (strokingColor.toRGB() != COLOR_WHITE) {
                    rectList.add(linePath.getBounds());
                }
            }
            linesCount = 0;
            linePath.reset();

        }

        @Override
        public void strokePath() throws IOException {
            PDColor strokingColor = getGraphicsState().getStrokingColor();
            try {
                if (strokingColor.toRGB() != COLOR_WHITE) {
                    rectList.add(linePath.getBounds2D());
                }
            } catch(Throwable t) {
                System.err.println(t.getMessage());
                rectList.add(linePath.getBounds2D());
            }
            linePath.reset();
        }

        @Override
        public void fillPath(int windingRule) throws IOException {
            if (linesCount == 3) {
                PDColor strokingColor = getGraphicsState().getStrokingColor();
                if (strokingColor.toRGB() != COLOR_WHITE) {
                    rectList.add(linePath.getBounds());
                }
            }
            linesCount = 0;
            linePath.reset();
        }

        @Override
        public void fillAndStrokePath(int windingRule) throws IOException {
            linesCount = 0;
            linePath.reset();
        }


        @Override
        public void shadingFill(COSName cosn) throws IOException {
        }
    }
}
