package sciscore.key_resource_table_extractor.table_transformer;

import com.google.common.collect.Range;
import org.json.JSONArray;
import org.json.JSONObject;
import sciscore.key_resource_table_extractor.FileUtils;
import sciscore.key_resource_table_extractor.common.CharSetEncoding;
import sciscore.key_resource_table_extractor.common.Rectangle;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class PDFTable {
    private final float left, top, right, bottom;
    private final List<Row> rows = new ArrayList<>(20);
    private float scaleX, scaleY;
    private int pageHeight, pageWidth;

    public PDFTable(float left, float top, float right, float bottom, int pageHeight, int pageWidth) {
        this.left = left;
        this.top = top;
        this.right = right;
        this.bottom = bottom;
        this.pageWidth = pageWidth;
        this.pageHeight = pageHeight;
    }

    public void addRow(Row row) {
        rows.add(row);
    }

    public float getLeft() {
        return left;
    }

    public float getTop() {
        return top;
    }

    public float getRight() {
        return right;
    }

    public float getBottom() {
        return bottom;
    }

    public List<Row> getRows() {
        return rows;
    }

    public int getPageHeight() {
        return pageHeight;
    }

    public int getPageWidth() {
        return pageWidth;
    }

    public void calcScaleFactors(float pdfWidth, float pdfHeight) {
        this.scaleX = pdfWidth / (pageWidth);
        this.scaleY = pdfHeight / (pageHeight);
    }

    public Rectangle getBounds() {
        int width = (int) ((right - left) * scaleX);
        int height = (int) ((bottom - top) * scaleY);
        // return new Rectangle((int) left * scaleX, (int)  top * scaleY, width, height);
        return new Rectangle((int) top * scaleX, (int) left * scaleY, width, height);
    }

    public int getEffectiveColumnNumber() {
        List<Integer> colSizes = new ArrayList<>(rows.size());
        for (Row row : rows) {
            colSizes.add(row.getCells().size());
        }
        Collections.sort(colSizes);
        return colSizes.get((int) (colSizes.size() / 2.0));
    }

    public List<Range<Integer>> getColumnRanges() {
        int offset = (int) (left);
        List<Range<Integer>> columnRanges = new ArrayList<>(5);
        int numCols = getEffectiveColumnNumber();
        for (int i = 0; i < numCols; i++) {
            float xmin = Float.MAX_VALUE, xmax = -1;
            for (Row row : rows) {
                if (i >= row.getCells().size()) {
                    continue;
                }
                RowCell cell = row.getCells().get(i);
                if (xmin > cell.getLeft()) {
                    xmin = cell.getLeft();
                }
                if (xmax < cell.getRight()) {
                    xmax = cell.getRight();
                }
            }
            float lb = (float) (Math.floor(xmin) - 1) + offset;
            float ub = (float) (Math.ceil(xmax) + 1) + offset;
            Range<Integer> range = Range.closed((int) (lb * scaleX), (int) (ub * scaleX));
            columnRanges.add(range);
        }
        return columnRanges;
    }

    public List<Range<Integer>> getRowRanges() {
        int offset = (int) (top); // was left
        List<Range<Integer>> rowRanges = new ArrayList<>(rows.size());
        for (Row row : rows) {
            float lb = (float) (Math.floor(row.getTop()) - 1) + offset;
            float ub = (float) (Math.ceil(row.getBottom()) + 1) + offset;
            Range<Integer> range = Range.closed((int) (lb * scaleX), (int) (ub * scaleX));
            rowRanges.add(range);
        }
        return rowRanges;
    }


    public static PDFTable fromJSON(JSONObject json) {
        float left = json.getFloat("left");
        float top = json.getFloat("top");
        float right = json.getFloat("right");
        float bottom = json.getFloat("bottom");
        int pageHeight = json.getInt("page_height");
        int pageWidth = json.getInt("page_width");

        PDFTable table = new PDFTable(left, top, right, bottom, pageHeight,
                pageWidth);
        JSONArray jsArr = json.getJSONArray("rows");
        for (int i = 0; i < jsArr.length(); i++) {
            table.addRow(Row.fromJSON(jsArr.getJSONObject(i)));
        }
        return table;
    }


    public static void main(String[] args) throws IOException {
        String jsonPath = "/tmp/tables/media-8/media-8_page_1_table_1.json";
        String jsonStr = FileUtils.loadAsString(jsonPath, CharSetEncoding.UTF8);
        JSONObject json = new JSONObject(jsonStr);
        PDFTable table = PDFTable.fromJSON(json);

        System.out.println(table.getLeft());

    }
}
