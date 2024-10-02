package sciscore.key_resource_table_extractor.table_transformer;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

public class Row {
    private float left, top, right, bottom;
    List<RowCell> cells = new ArrayList<>(5);

    public Row(float left, float top, float right, float bottom) {
        this.left = left;
        this.top = top;
        this.right = right;
        this.bottom = bottom;
    }

    public void addCell(RowCell cell) {
        cells.add(cell);
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

    public List<RowCell> getCells() {
        return cells;
    }



    public static Row fromJSON(JSONObject json) {
        float left = json.getFloat("left");
        float top = json.getFloat("top");
        float right = json.getFloat("right");
        float bottom = json.getFloat("bottom");
        Row row = new Row(left, top, right, bottom);
        JSONArray jsArr = json.getJSONArray("cells");
        for(int i = 0; i < jsArr.length(); i++) {
            row.addCell( RowCell.fromJSON(jsArr.getJSONObject(i)));
        }
        return row;
    }
}
