package sciscore.key_resource_table_extractor;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

class TextPositionExtractor extends PDFTextStripper {

    private final List<TextPosition> textPositions = new ArrayList<>();
    private final int pageId;
    private boolean verbose = false;

    TextPositionExtractor(PDDocument document, int pageId) {
        super();
        super.setSortByPosition(true);
        super.document = document;
        this.pageId = pageId;
    }

    public boolean isVerbose() {
        return verbose;
    }

    public void setVerbose(boolean verbose) {
        this.verbose = verbose;
    }

    public void stripPage(int pageId) throws IOException {
        this.setStartPage(pageId + 1);
        this.setEndPage(pageId + 1);
        try (Writer writer = new OutputStreamWriter(new ByteArrayOutputStream())) {
            writeText(document, writer);
        }
    }

    @Override
    protected void writeString(String string, List<TextPosition> textPositions) {
        this.textPositions.addAll(textPositions);

        if (verbose) {
            if (this.pageId == 14) {
                StringBuilder sb = new StringBuilder();
                for (TextPosition text : textPositions) {
                    sb.append(text.getUnicode());
                }
                System.out.println(sb.toString());
                for (TextPosition text : textPositions) {
                    System.out.println("String[" + text.getXDirAdj() + "," +
                            text.getYDirAdj() + " fs=" + text.getFontSize() + " xscale=" +
                            text.getXScale() + " height=" + text.getHeightDir() + " space=" +
                            text.getWidthOfSpace() + " width=" +
                            text.getWidthDirAdj() + "] " + text.getUnicode());
                }
            }
        }
    }

    /**
     * and order by textPosition.getY() ASC
     *
     * @return
     * @throws IOException
     */
    public List<TextPosition> extract() throws IOException {
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
