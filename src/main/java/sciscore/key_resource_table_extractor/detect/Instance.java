package sciscore.key_resource_table_extractor.detect;

import org.json.JSONObject;

public class Instance {
    String id;
    String currentLine;
    String previousLine;
    boolean hasVerticalLines = false;
    boolean hasHorizontalLines = false;
    boolean hasVerticalLines2 = false;
    boolean hasHorizontalLines2 = false;
    String label;
    String pageId;

    public Instance(String id, String currentLine,
                    String previousLine, boolean hasVerticalLines,
                    boolean hasHorizontalLines, String label,
                    boolean hasVerticalLines2,
                    boolean hasHorizontalLines2,
                    String pageId) {
        this.id = id;
        this.currentLine = currentLine;
        this.previousLine = previousLine;
        this.hasVerticalLines = hasVerticalLines;
        this.hasHorizontalLines = hasHorizontalLines;
        this.label = label;
        this.hasVerticalLines2 = hasVerticalLines2;
        this.hasHorizontalLines2 = hasHorizontalLines2;
        this.pageId = pageId;
    }

    public String getId() {
        return id;
    }

    public String getCurrentLine() {
        return currentLine;
    }

    public String getPreviousLine() {
        return previousLine;
    }

    public boolean isHasVerticalLines() {
        return hasVerticalLines;
    }

    public boolean isHasHorizontalLines() {
        return hasHorizontalLines;
    }

    public String getLabel() {
        return label;
    }

    public boolean isHasVerticalLines2() {
        return hasVerticalLines2;
    }

    public boolean isHasHorizontalLines2() {
        return hasHorizontalLines2;
    }

    public String getPageId() {
        return pageId;
    }

    public void setLabel(String label) {
        this.label = label;
    }

    public void setId(String id) {
        this.id = id;
    }

    public JSONObject toJSON() {
        JSONObject json = new JSONObject();
        json.put("currentLine", currentLine);
        json.put("previousLine", previousLine);
        json.put("id", id);
        json.put("hasVerticalLines", hasVerticalLines);
        json.put("hasHorizontalLines", hasHorizontalLines);
        json.put("hasVerticalLines2", hasVerticalLines);
        json.put("hasHorizontalLines2", hasHorizontalLines);
        json.put("label", label);
        json.put("pageId", pageId);
        return json;
    }
    public static Instance fromJSON(JSONObject json) {
        String currentLine = json.getString("currentLine");
        String previousLine = json.getString("previousLine");
        String id = json.getString("id");
        String label = json.getString("label");
        String pageId = json.getString("pageId");
        boolean hasVerticalLines = json.getBoolean("hasVerticalLines");
        boolean hasVerticalLines2 = json.getBoolean("hasVerticalLines2");
        boolean hasHorizontalLines = json.getBoolean("hasHorizontalLines");
        boolean hasHorizontalLines2 = json.getBoolean("hasHorizontalLines2");
        return new Instance(id, currentLine, previousLine, hasVerticalLines,
                hasHorizontalLines, label, hasVerticalLines2,
                hasHorizontalLines2, pageId);
    }
}
