package sciscore.key_resource_table_extractor.table_transformer;

import org.json.JSONObject;

public class RowCell {
    private int span = 1;
    private String text;
    private float left, top, right, bottom;

    public RowCell(int span, float left, float top, float right, float bottom) {
        this.span = span;
        this.left = left;
        this.top = top;
        this.right = right;
        this.bottom = bottom;
    }

    public void setText(String text) {
        this.text = text;
    }

    public int getSpan() {
        return span;
    }

    public String getText() {
        return text;
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


    @Override
    public String toString() {
        final StringBuilder sb = new StringBuilder("RowCell{");
        sb.append("span=").append(span);
        sb.append(", text='").append(text).append('\'');
        sb.append(", left=").append(left);
        sb.append(", top=").append(top);
        sb.append(", right=").append(right);
        sb.append(", bottom=").append(bottom);
        sb.append('}');
        return sb.toString();
    }

    public static RowCell fromJSON(JSONObject json) {
        int span = json.getInt("span");
        float left = json.getFloat("left");
        float top = json.getFloat("top");
        float right = json.getFloat("right");
        float bottom = json.getFloat("bottom");
        RowCell cell = new RowCell(span, left, top, right, bottom);
        cell.text = json.getString("text");
        return cell;
    }
}
