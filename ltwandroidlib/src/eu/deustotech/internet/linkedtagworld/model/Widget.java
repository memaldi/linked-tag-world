package eu.deustotech.internet.linkedtagworld.model;

/**
 * Created by mikel on 22/05/13.
 */
/**
 * Representation of an Android Widget.
 * @author mikel
 *
 */
public class Widget {
    private String id;
    private boolean clickable;
    private boolean main;

    /**
     * Constructor.
     * @param id the id of the widget.
     * @param clickable specifies if the widget renders a clickable property.
     * @param main specifies if the widget renders a main property.
     */
    public Widget(String id, boolean clickable, boolean main) {
        this.id = id;
        this.clickable = clickable;
        this.main = main;
    }

    /**
     * Default constructor, clickable and main equals to False.
     * @param id the id of the widget.
     */
    public Widget(String id) {
        this.id = id;
        this.clickable = false;
        this.main = false;
    }

    /**
     * Returns if the widget renders a clickable property.
     * @return True if renders a clickable property, False if not.
     */
    public boolean isClickable() {
        return clickable;
    }

    /**
     * Sets if the widget renders a clickable property.
     * @param clickable True if renders a clickable property, False if not.
     */
    public void setClickable(boolean clickable) {
        this.clickable = clickable;
    }

    /**
     * Returns the id of the widget.
     * @return the id of the widget.
     */
    public String getId() {
        return id;
    }

    /**
     * Sets the id of the widget.
     * @param id the id of the widget.
     */
    public void setId(String id) {
        this.id = id;
    }

    /**
     * Returns if the widget is rendering a main property of an entity.
     * @return True if the widget is rendering a main property of an entity, False if not.
     */
    public boolean isMain() {
        return main;
    }

    /**
     * Sets if the widget is rendering a main property of an entity.
     * @param main True if the widget is rendering a main property of an entity, False if not.
     */
    public void setMain(boolean main) {
        this.main = main;
    }
}
