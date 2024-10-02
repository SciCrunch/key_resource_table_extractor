package sciscore.key_resource_table_extractor.common;

import java.awt.geom.Point2D;
import java.awt.geom.Rectangle2D;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

@SuppressWarnings("serial")
public class Rectangle extends Rectangle2D.Float {


	public static final Comparator<Rectangle> AREA_ORDER = new Comparator<Rectangle>() {
		@Override
		public int compare(Rectangle o1, Rectangle o2) {
			if (o1.equals(o2)) return 0;
			float area1 = o1.getArea();
			float area2 = o2.getArea();
			if (area1 > area2) {
				return -1;
			} else if (area1 < area2) {
				return 1;
			}
			return 0;
		}
	};

	public static final Comparator<Rectangle> COLUMN_ORDER = new Comparator<Rectangle>() {
		@Override
		public int compare(Rectangle o1, Rectangle o2) {
			if (o1.equals(o2)) return 0;
			if (o1.height > o2.height) {
				return -1;
			} else if (o1.height < o2.height) {
				return 1;
			} else {
				if (o1.x > o2.x) {
					return 1;
				} else if (o1.x < o2.x) {
					return -1;
				}
			}
			return 0;
		}
	};

	public static final Comparator<Rectangle> ROW_ORDER = new Comparator<Rectangle>() {
		@Override
		public int compare(Rectangle o1, Rectangle o2) {
			if (o1.equals(o2)) return 0;
			/*
			if (o1.width > o2.width) {
				return -1;
			} else if (o1.width < o2.width) {
				return 1;
			} else {
			*/
				if (o1.y > o2.y) {
					return 1;
				} else if (o1.y < o2.y) {
					return -1;
				}

			//}
			return 0;
		}
	};
	
	protected static final float VERTICAL_COMPARISON_THRESHOLD = 0.4f;

	public Rectangle() {
		super();
	}

	public Rectangle(float top, float left, float width, float height) {
		super();
		this.setRect(left, top, width, height);
	}


	public int isLtrDominant() {
		return 0;
	}

	public float getArea() {
		return this.width * this.height;
	}

	public float verticalOverlap(Rectangle other) {
		return Math.max(0, Math.min(this.getBottom(), other.getBottom()) - Math.max(this.getTop(), other.getTop()));
	}

	public boolean verticallyOverlaps(Rectangle other) {
		return verticalOverlap(other) > 0;
	}

	public float horizontalOverlap(Rectangle other) {
		return Math.max(0, Math.min(this.getRight(), other.getRight()) - Math.max(this.getLeft(), other.getLeft()));
	}

	public boolean horizontallyOverlaps(Rectangle other) {
		return horizontalOverlap(other) > 0;
	}

	public float verticalOverlapRatio(Rectangle other) {
		float rv = 0, delta = Math.min(this.getBottom() - this.getTop(), other.getBottom() - other.getTop());

		if (other.getTop() <= this.getTop() && this.getTop() <= other.getBottom()
				&& other.getBottom() <= this.getBottom()) {
			rv = (other.getBottom() - this.getTop()) / delta;
		} else if (this.getTop() <= other.getTop() && other.getTop() <= this.getBottom()
				&& this.getBottom() <= other.getBottom()) {
			rv = (this.getBottom() - other.getTop()) / delta;
		} else if (this.getTop() <= other.getTop() && other.getTop() <= other.getBottom()
				&& other.getBottom() <= this.getBottom()) {
			rv = (other.getBottom() - other.getTop()) / delta;
		} else if (other.getTop() <= this.getTop() && this.getTop() <= this.getBottom()
				&& this.getBottom() <= other.getBottom()) {
			rv = (this.getBottom() - this.getTop()) / delta;
		}

		return rv;

	}

	public float overlapRatio(Rectangle other) {
		double intersectionWidth = Math.max(0,
				Math.min(this.getRight(), other.getRight()) - Math.max(this.getLeft(), other.getLeft()));
		double intersectionHeight = Math.max(0,
				Math.min(this.getBottom(), other.getBottom()) - Math.max(this.getTop(), other.getTop()));
		double intersectionArea = Math.max(0, intersectionWidth * intersectionHeight);
		double unionArea = this.getArea() + other.getArea() - intersectionArea;

		return (float) (intersectionArea / unionArea);
	}

	public Rectangle merge(Rectangle other) {
		this.setRect(this.createUnion(other));
		return this;
	}

	public float getTop() {
		return (float) this.getMinY();
	}

	public void setTop(float top) {
		float deltaHeight = top - this.y;
		this.setRect(this.x, top, this.width, this.height - deltaHeight);
	}

	public float getRight() {
		return (float) this.getMaxX();
	}

	public void setRight(float right) {
		this.setRect(this.x, this.y, right - this.x, this.height);
	}

	public float getLeft() {
		return (float) this.getMinX();
	}

	public void setLeft(float left) {
		float deltaWidth = left - this.x;
		this.setRect(left, this.y, this.width - deltaWidth, this.height);
	}

	public float getBottom() {
		return (float) this.getMaxY();
	}

	public void setBottom(float bottom) {
		this.setRect(this.x, this.y, this.width, bottom - this.y);
	}

	public Point2D[] getPoints() {
		return new Point2D[] { new Point2D.Float(this.getLeft(), this.getTop()),
				new Point2D.Float(this.getRight(), this.getTop()), new Point2D.Float(this.getRight(), this.getBottom()),
				new Point2D.Float(this.getLeft(), this.getBottom()) };
	}

	@Override
	public String toString() {
		StringBuilder sb = new StringBuilder();
		String s = super.toString();
		sb.append(s.substring(0, s.length() - 1));
		sb.append(String.format(Locale.US, ",bottom=%f,right=%f]", this.getBottom(), this.getRight()));
		return sb.toString();
	}

	/**
	 * @param rectangles
	 * @return minimum bounding box that contains all the rectangles
	 */
	public static Rectangle boundingBoxOf(List<? extends Rectangle> rectangles) {
		float minx = java.lang.Float.MAX_VALUE;
		float miny = java.lang.Float.MAX_VALUE;
		float maxx = java.lang.Float.MIN_VALUE;
		float maxy = java.lang.Float.MIN_VALUE;

		for (Rectangle r : rectangles) {
			minx = (float) Math.min(r.getMinX(), minx);
			miny = (float) Math.min(r.getMinY(), miny);
			maxx = (float) Math.max(r.getMaxX(), maxx);
			maxy = (float) Math.max(r.getMaxY(), maxy);
		}
		return new Rectangle(miny, minx, maxx - minx, maxy - miny);
	}

}
