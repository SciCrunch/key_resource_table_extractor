package sciscore.key_resource_table_extractor.common;

import java.util.ArrayList;
import java.util.List;

/**
 * Created by bozyurt on 12/9/22.
 */
public class TableRow {
    private final int idx;
    private final List<TableCell> cells = new ArrayList<>();

    public TableRow(int idx) {
        this.idx = idx;
    }

    public int getIdx() {
        return idx;
    }

    public List<TableCell> getCells() {
        return cells;
    }

    @Override
    public String toString() {
        StringBuilder retVal = new StringBuilder();
        int lastCellIdx = 0;
        for (TableCell cell : cells) {
            for (int idx2 = lastCellIdx; idx2 < cell.getIdx() - 1; idx2++) {
                retVal.append(";");
            }
            if (cell.getIdx() > 0) {
                retVal.append(";");
            }
            retVal.append(cell.getContent());
            lastCellIdx = cell.getIdx();
        }
        //return
        return retVal.toString();
    }

}
