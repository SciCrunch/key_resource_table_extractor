package sciscore.key_resource_table_extractor.detect;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;
import sciscore.key_resource_table_extractor.LineExtractor;
import sciscore.key_resource_table_extractor.PDFUtils;
import sciscore.key_resource_table_extractor.common.Rectangle;
import sciscore.key_resource_table_extractor.common.SimpleSequentialIDGenerator;

import java.io.*;
import java.util.*;

/**
 * Created by bozyurt on 12/21/22.
 */

@SuppressWarnings("Duplicates")
public class FeatureGenerator {
    private String pdfFile;

    public FeatureGenerator(String pdfFile) {
        this.pdfFile = pdfFile;
    }

    public List<Instance> handle(SimpleSequentialIDGenerator idGenerator) throws Exception {
        Map<Integer, List<Rectangle>> page2LinesMap = LineExtractor.extractLines(this.pdfFile);
        Map<Integer, List<TextPosition>> page2TextPosMap = new HashMap<>();
        Map<Integer, Rectangle> pageBoundsMap = PDFUtils.getPageBounds(this.pdfFile);
        PDDocument doc = null;
        List<Instance> instances = new ArrayList<>();
        String prevRowContent = null;
        boolean prevHasVerticalLines = false;
        boolean prevHasHorizontalLines = false;
        boolean first = true;
        try {
            doc = Loader.loadPDF(new File(this.pdfFile));
            for (int pageId = 0; pageId < doc.getNumberOfPages(); pageId++) {
                List<TextPosition> texts = extractTextPositions(doc, pageId);
                page2TextPosMap.put(pageId, texts);
                List<Rectangle> rectList = page2LinesMap.get(pageId);
                Rectangle pageBounds = pageBoundsMap.get(pageId);
                rectList = filter(rectList, pageBounds);
                List<RowText> rows = getTextRows(texts);
                System.out.println("Page " + (pageId + 1));
                System.out.println("-----------------------");
                for (RowText row : rows) {
                    boolean overlappingVerticalLines = hasOverlappingVerticalLines(row, rectList);
                    boolean overlappingHorizontalLines = hasOverlappingHorizontalLines(row, rectList);

                    if (overlappingVerticalLines) {
                        if (overlappingHorizontalLines) {
                            System.out.println("*+  " + row.getRowContent());
                        } else {
                            System.out.println("*  " + row.getRowContent());
                        }
                    } else {
                        if (overlappingHorizontalLines) {
                            System.out.println("+  " + row.getRowContent());
                        } else {
                            System.out.println(row.getRowContent());
                        }
                    }
                    if (first) {
                        prevRowContent = row.getRowContent();
                        prevHasVerticalLines = overlappingVerticalLines;
                        prevHasHorizontalLines = overlappingHorizontalLines;
                        first = false;
                    } else {
                        String label = "none";
                        String rowContent = row.getRowContent();
                        int id = idGenerator.nextID();
                        Instance inst = new Instance(String.valueOf(id),
                                rowContent, prevRowContent,
                                overlappingVerticalLines, overlappingHorizontalLines,
                                label, prevHasVerticalLines, prevHasHorizontalLines,
                                String.valueOf(pageId));
                        instances.add(inst);
                        prevRowContent = rowContent;
                        prevHasVerticalLines = overlappingVerticalLines;
                        prevHasHorizontalLines = overlappingHorizontalLines;
                    }
                }
            }
        } finally {
            if (doc != null) {
                doc.close();
            }
        }
        return instances;
    }

    public static void prepInstances(String pdfFile, String outJSONFile,
                                     SimpleSequentialIDGenerator idGen) throws Exception {
        FeatureGenerator fg = new FeatureGenerator(pdfFile);
        List<Instance> instances = fg.handle(idGen);
        DataPrepUtils.saveInstances(instances, outJSONFile);
    }

    public static List<Rectangle> filter(List<Rectangle> rectList, Rectangle pageBounds) {
        List<Rectangle> filtered = new ArrayList<>(rectList.size());
        for (Rectangle rect : rectList) {
            if (pageBounds.contains(rect)) {
                filtered.add(rect);
            }
        }
        return filtered;
    }

    public static boolean hasOverlappingVerticalLines(RowText row,
                                                      List<Rectangle> rectList) {
        Rectangle bounds = row.getBounds();
        for (Rectangle rect : rectList) {
            if (bounds.verticallyOverlaps(rect)) {
                return true;
            }
        }
        return false;
    }

    public static boolean hasOverlappingHorizontalLines(RowText row, List<Rectangle> rectList) {
        Rectangle bounds = row.getBounds();
        for (Rectangle rect : rectList) {
            float diff = rect.getTop() - bounds.getBottom();
            double r = widthOverlapRatio(bounds, rect);
            if (Math.abs(diff) < 4 && r > 0.5) {
                return true;
            }
        }
        return false;
    }


    public static double widthOverlapRatio(Rectangle bounds, Rectangle rect) {
        return bounds.getWidth() / rect.getWidth();
    }


    static List<RowText> getTextRows(List<TextPosition> texts) {
        Map<Float, RowText> sameYMap = new LinkedHashMap<>();
        for (TextPosition tp : texts) {
            Float y = tp.getY();

            RowText row = sameYMap.get(y);
            if (row == null) {
                row = new RowText(y);
                sameYMap.put(y, row);
            }
            row.add(tp);
        }
        List<RowText> list = new ArrayList<>(sameYMap.values());
        List<RowText> merged = new ArrayList<>();
        while (!list.isEmpty()) {
            RowText row1 = list.get(0);
            if (list.size() > 1) {
                RowText row2 = list.get(1);
                float diff = Math.abs(row2.getY() - row1.getY());
                if (diff < 3) {
                    row1.getTpList().addAll(row2.getTpList());
                    merged.add(row1);
                    row1.organize();
                    list.remove(0);
                    list.remove(0);
                } else {
                    merged.add(row1);
                    list.remove(0);
                }
            } else {
                merged.add(row1);
                list.remove(0);
            }
        }

        return merged;
    }

    static List<TextPosition> extractTextPositions(PDDocument document, int pageId) throws IOException {
        TextPositionExtractor extractor = new TextPositionExtractor(document, pageId);
        System.out.println("average Char Tolerance: " + extractor.getAverageCharTolerance());
        return extractor.extract();
    }

    public static float getMean(List<Float> values) {
        double sum = 0;
        for(float value : values) {
            sum += value;
        }
        return (float) (sum/ values.size());
    }

    public static class RowText {
        float y;
        List<TextPosition> tpList = new ArrayList<>(20);

        public RowText(float y) {
            this.y = y;
        }

        public void add(TextPosition tp) {
            tpList.add(tp);
        }

        public float getY() {
            return y;
        }

        public List<TextPosition> getTpList() {
            return tpList;
        }

        public void organize() {
            Collections.sort(tpList, (o1, o2) -> Float.compare(o1.getX(), o2.getX()));
        }

        public Rectangle getBounds() {
            float minX = Float.MAX_VALUE, minY = Float.MAX_VALUE;
            float maxX = -1, maxY = -1;
            for (TextPosition tp : tpList) {
                if (tp.getX() < minX) {
                    minX = tp.getX();
                }
                if (tp.getY() < minY) {
                    minY = tp.getY();
                }
                if (tp.getX() + tp.getWidth() > maxX) {
                    maxX = tp.getX() + tp.getWidth();
                }
                if (tp.getY() + tp.getHeight() > maxY) {
                    maxY = tp.getY() + tp.getHeight();
                }
            }
            return new Rectangle(minY, minX, maxX - minX, maxY - minY);
        }

        public float getSpacingThreshold(boolean verbose) {
            if (tpList.size() < 5) {
                return -1;
            }
            List<Float> widths = new ArrayList<>();
            for(TextPosition tp : tpList) {
                widths.add( tp.getWidth());
            }
            float avgWidth = getMean(widths);
            List<Float> spacingList = new ArrayList<>(tpList.size() - 1);
            float prev = tpList.get(0).getX() + tpList.get(0).getWidth();
            for(int i = 1; i < tpList.size(); i++) {
                float cur = tpList.get(i).getX();
                spacingList.add( Math.max(cur - prev, 0));
                prev = tpList.get(i).getX() + tpList.get(i).getWidth();
            }
            Collections.sort(spacingList);
            double sum = 0;
            double min = Double.MAX_VALUE, max = -1;
            int count = 0;
            for(float f: spacingList) {
                if (f <= 0) {
                    continue;
                }
                sum += f;
                if (f > max) {
                    max = f;
                }
                if (f < min) {
                    min = f;
                }
                count++;
            }
            if (verbose) {
                float fontSizeInPt = tpList.get(0).getFontSizeInPt();
                String value = tpList.get(0).getFont().getName();
                System.out.println("spacing min:" + min + " max:" + max + " avg width:" + avgWidth +
                        " font size:" + fontSizeInPt + " avg font width:" + value);
            }
            if (count == 0) {
                return -1;
            }
            // return Math.min((float) (1.2 * sum / count), (float)(avgWidth * 0.4));
            return Math.min((float)max, (float)(avgWidth * 0.4));

            //int mid = spacingList.size() / 2;
            //return spacingList.get(mid);
        }

        public String getRowContent() {
            boolean verbose = false;
            float spacingThreshold = getSpacingThreshold(verbose);
            if (spacingThreshold > 0) {
                // System.out.println("spacingThreshold:" + spacingThreshold);
            }

            StringBuilder sb = new StringBuilder();
            float prevX = -1;
            float spacing = -1;
            for (int idx = 0; idx < tpList.size(); idx++) {
                TextPosition tp = tpList.get(idx);
                String st = tp.getUnicode();
                if (prevX < 0) {
                    prevX = tp.getX() + tp.getWidth();
                } else {
                    spacing = tp.getX() - prevX;
                    prevX = tp.getX() + tp.getWidth();
                }

                if (spacingThreshold > 0 && st.length() ==1 && !Character.isSpaceChar(st.charAt(0))) {
                    if (spacing > spacingThreshold) {
                        if (idx+1 < tpList.size()) {
                            TextPosition tpn = tpList.get(idx + 1);
                            String stn = tpn.getUnicode();
                            if (stn.length() > 1 || (!Character.isSpaceChar(stn.charAt(0)) &&
                                    !Character.isSpaceChar(sb.charAt(sb.length() -1)))) {
                                if (verbose) {
                                    System.out.println(spacing + " > " + spacingThreshold +  " for " + sb.toString());
                                }
                                sb.append(' ');
                            }
                        }
                    }
                }
                sb.append(st);
            }
            return sb.toString();
        }
    }

    public static class TextPositionExtractor extends PDFTextStripper {

        private final List<TextPosition> textPositions = new ArrayList<>();
        private final int pageId;

        private TextPositionExtractor(PDDocument document, int pageId) throws IOException {
            super();
            super.setSortByPosition(true);
            super.document = document;
            this.pageId = pageId;
        }

        public void stripPage(int pageId) throws IOException {
            this.setStartPage(pageId + 1);
            this.setEndPage(pageId + 1);
            try (Writer writer = new OutputStreamWriter(new ByteArrayOutputStream())) {
                writeText(document, writer);
            }
        }

        @Override
        protected void writeString(String string, List<TextPosition> textPositions) throws IOException {
            this.textPositions.addAll(textPositions);
        }

        /**
         * and order by textPosition.getY() ASC
         *
         * @return
         * @throws IOException
         */
        private List<TextPosition> extract() throws IOException {
            this.stripPage(pageId);
            //sort
            Collections.sort(textPositions, (o1, o2) -> {
                int retVal = 0;
                if (o1.getY() < o2.getY()) {
                    retVal = -1;
                } else if (o1.getY() > o2.getY()) {
                    retVal = 1;
                }
                return retVal;

            });
            return this.textPositions;
        }
    }
}
