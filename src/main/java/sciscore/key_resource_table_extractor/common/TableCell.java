package sciscore.key_resource_table_extractor.common;

/**
 * Created by bozyurt on 12/9/22.
 */
public class TableCell {
    private final String content;
    private final int idx;
    private Rectangle bounds;

    public TableCell(int idx, String content) {
        this.idx = idx;
        this.content = content;
    }

    public TableCell(int idx, String content, Rectangle bounds) {
        this.idx = idx;
        this.content = content;
        this.bounds = bounds;
    }

    public String getContent() {
        return content;
    }

    public int getIdx() {
        return idx;
    }

    public Rectangle getBounds() {
        return bounds;
    }

    public void setBounds(Rectangle bounds) {
        this.bounds = bounds;
    }
}
