package eu.deustotech.internet.linkedtagworld.model;

/**
 * Created by mikel on 22/05/13.
 */
public class Widget {
    private String id;
    private boolean clickable;
    private boolean main;

    public Widget(String id, boolean clickable, boolean main) {
        this.id = id;
        this.clickable = clickable;
        this.main = main;
    }

    public Widget(String id) {
        this.id = id;
        this.clickable = false;
        this.main = false;
    }

    public boolean isClickable() {
        return clickable;
    }

    public void setClickable(boolean clickable) {
        this.clickable = clickable;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public boolean isMain() {
        return main;
    }

    public void setMain(boolean main) {
        this.main = main;
    }
}
