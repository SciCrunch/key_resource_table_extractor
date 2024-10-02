package sciscore.key_resource_table_extractor;

import com.google.common.collect.Range;

/**
 * Created by bozyurt on 12/12/22.
 */
public class Utils {

    public static double overlapRatio(Range<Integer> first, Range<Integer> second) {
        if (first.upperEndpoint() > second.lowerEndpoint() &&
                first.upperEndpoint() <= second.upperEndpoint()) {
            return (first.upperEndpoint() - second.lowerEndpoint()) /
                    (double) (first.upperEndpoint() - first.lowerEndpoint());
        } else if (first.lowerEndpoint() > second.lowerEndpoint() &&
                first.upperEndpoint() > second.upperEndpoint()) {
            return (second.upperEndpoint() - first.lowerEndpoint()) /
                    (double) (first.upperEndpoint() - first.lowerEndpoint());
        }

        return 0;
    }
}
